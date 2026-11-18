from datetime import date, timedelta

import pandas as pd
import pytest

from license_pipeline import config
from license_pipeline.generate import generate, generate_clean

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
TODAY = config.TODAY


@pytest.fixture(scope="module")
def raw():
    return generate()


@pytest.fixture(scope="module")
def clean():
    return generate_clean()


@pytest.fixture(scope="module")
def truth(clean):
    return clean["ground_truth"]


def refs(truth, rule):
    return set(truth.loc[truth["rule"] == rule, "record_ref"])


def valid_contracts(clean):
    c = clean["contracts"]
    ok = c["renewal_date"].map(lambda d: isinstance(d, date))
    c = c[ok & (c["owner_id"] != "") & (c["seats_purchased"] > 0)]
    c = c[c["renewal_date"] > c["start_date"]]
    return c.drop_duplicates("contract_id")


def test_generation_is_deterministic():
    a, b = generate(), generate()
    assert a.keys() == b.keys()
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_raw_tables_present(raw):
    expected = {"owners", "contracts", "inventory", "usage", "ai_seats", "ground_truth"}
    assert expected <= set(raw)


def test_contract_row_count_includes_injected_extras(raw):
    assert len(raw["contracts"]) == config.N_CONTRACTS + 4 * config.INJECT_PER_RULE


def test_raw_contracts_do_not_leak_site(raw):
    assert "site_id" not in raw["contracts"].columns
    assert "_product_id" not in raw["inventory"].columns


def test_raw_usage_has_no_label_columns(raw):
    usage = raw["usage"]
    assert len(usage) == config.N_USAGE_SEATS
    assert not any(col.startswith("_") for col in usage.columns)


def test_unused_share_from_clean(clean):
    usage = clean["usage"]
    cutoff = TODAY - timedelta(days=config.UNUSED_DAYS)
    share = (usage["last_active_date"] < cutoff).mean()
    assert 0.36 <= share <= 0.38


def test_dates_use_mixed_formats(raw):
    col = raw["contracts"]["renewal_date"].astype(str)
    assert col.str.match(r"^\d{4}-\d{2}-\d{2}$").any()
    assert col.str.match(r"^\d{2}/\d{2}/\d{4}$").any()
    assert col.str.match(rf"^\d{{1,2}} ({'|'.join(MONTHS)}) \d{{4}}$").any()


def test_inventory_names_are_messy(raw):
    assert raw["inventory"]["raw_name"].nunique() > 40


@pytest.mark.parametrize(
    "rule",
    [
        "renewal_30", "renewal_60", "renewal_90", "price_change_renewal",
        "installs_over_entitlement", "usage_spike",
        "duplicate", "missing_owner", "invalid_date", "negative_seats", "unmapped_product",
    ],
)
def test_each_injected_rule_has_eight_truth_rows(truth, rule):
    assert len(refs(truth, rule)) == config.INJECT_PER_RULE


@pytest.mark.parametrize("rule", ["contract_without_inventory", "inventory_without_contract"])
def test_structural_dq_truth_not_empty(truth, rule):
    assert len(refs(truth, rule)) > 0


def test_renewal_tiers_match_dates(clean, truth):
    c = valid_contracts(clean).set_index("contract_id")
    tiered = set()
    for window, lo, hi in config.RENEWAL_TIERS:
        for cid in refs(truth, f"renewal_{window}"):
            row = c.loc[cid]
            days = (row["renewal_date"] - TODAY).days - row["notice_days"]
            assert lo <= days <= hi
            tiered.add(cid)
    others = c.drop(index=list(tiered))
    days = others["renewal_date"].map(lambda d: (d - TODAY).days) - others["notice_days"]
    assert (days > 90).all()


def test_price_change_truth_matches_dates(clean, truth):
    c = valid_contracts(clean).merge(clean["catalog"], on="product_id")
    change = config.PRICE_CHANGES["Microsoft"]
    ms = c[c["publisher"] == "Microsoft"]
    flagged = ms[(ms["start_date"] < change) & (ms["renewal_date"] >= change)]
    assert set(flagged["contract_id"]) == refs(truth, "price_change_renewal")


def test_over_entitlement_truth_matches_installs(clean, truth):
    c = valid_contracts(clean).drop(columns="site_id")
    c = c.merge(clean["owners"][["owner_id", "site_id"]], on="owner_id")
    ent = c.groupby(["product_id", "site_id"])["seats_purchased"].sum()
    inv = clean["inventory"].dropna(subset=["_product_id"])
    latest = inv[inv["scan_date"] == inv["scan_date"].max()]
    installs = latest.groupby(["_product_id", "site_id"])["installs"].sum()
    joined = pd.concat([ent.rename("ent"), installs.rename("inst")], axis=1).dropna()
    over = {f"{p}|{s}" for (p, s), r in joined.iterrows() if r["inst"] > r["ent"]}
    assert over == refs(truth, "installs_over_entitlement")


def test_spike_truth_has_large_growth(clean, truth):
    inv = clean["inventory"].dropna(subset=["_product_id"])
    totals = inv.groupby(["_product_id", "site_id", "scan_date"])["installs"].sum().unstack()
    growth = totals.iloc[:, -1] / totals.iloc[:, -2] - 1
    spikes = {f"{p}|{s}" for (p, s), g in growth.items() if g > 0.5}
    assert spikes == refs(truth, "usage_spike")


def test_unused_truth_matches_last_active(clean, truth):
    cutoff = TODAY - timedelta(days=config.UNUSED_DAYS)
    seats = pd.concat([clean["usage"], clean["ai_seats"]])
    expected = set(seats.loc[seats["last_active_date"] < cutoff, "seat_id"])
    assert expected == refs(truth, "seat_unused_90d")


def test_write_raw_creates_csv_files(raw, tmp_path):
    from license_pipeline.generate import write_raw

    paths = write_raw(raw, tmp_path)
    assert {p.name for p in paths} >= {"contracts.csv", "inventory.csv", "ground_truth.csv"}
    assert pd.read_csv(tmp_path / "contracts.csv").shape == raw["contracts"].shape


def test_plan_rejects_too_few_normal_combos():
    import numpy as np

    from license_pipeline.synth_plan import plan_combos

    with pytest.raises(ValueError):
        plan_combos(np.random.default_rng(1), ["P1"], ["S1", "S2"], 0, 0, 8)
