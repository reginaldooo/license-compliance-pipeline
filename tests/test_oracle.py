"""Check the generator's ground truth against rules restated here from the README definitions."""

from datetime import date, timedelta

import pandas as pd
import pytest

from license_pipeline import config, scenarios
from license_pipeline.generate import generate_clean

TODAY = config.TODAY
SPIKE_TRUE_GROWTH = 0.5


def tier_for(days_to_notice: int) -> int | None:
    return next((w for w in (30, 60, 90) if days_to_notice <= w), None)


@pytest.fixture(scope="module", params=["baseline", "borderline", "messy", "conflict", "combined"])
def clean(request):
    return generate_clean(scenario=scenarios.get_scenario(request.param))


def truth_refs(clean, rule):
    t = clean["ground_truth"]
    return set(t.loc[t["rule"] == rule, "record_ref"])


def valid_contracts(clean):
    """Contracts the README says count as entitlements: no blocking data quality problem."""
    c = clean["contracts"]
    parsed = c["renewal_date"].map(lambda d: isinstance(d, date))
    c = c[parsed & (c["owner_id"] != "") & c["owner_id"].isin(clean["owners"]["owner_id"])]
    c = c[(c["seats_purchased"] > 0) & c["annual_cost"].notna() & c["notice_days"].notna()]
    c = c[(c["renewal_date"] > c["start_date"]) & (c["renewal_date"] >= TODAY)]
    distinct = clean["contracts"].drop_duplicates().groupby("contract_id").size()
    return c[~c["contract_id"].isin(distinct[distinct > 1].index)].drop_duplicates("contract_id")


def test_renewal_truth_matches_the_tier_definition(clean):
    c = valid_contracts(clean)
    days = c["renewal_date"].map(lambda d: (d - TODAY).days) - c["notice_days"]
    for window in (30, 60, 90):
        expected = set(c.loc[days.map(tier_for) == window, "contract_id"])
        assert expected == truth_refs(clean, f"renewal_{window}")


def test_unused_truth_matches_the_idle_definition(clean):
    cutoff = TODAY - timedelta(days=config.UNUSED_DAYS)
    seats = pd.concat([clean["usage"], clean["ai_seats"]])
    expected = set(seats.loc[seats["last_active_date"] < cutoff, "seat_id"])
    assert expected == truth_refs(clean, "seat_unused_90d")


def test_price_truth_matches_the_definition(clean):
    c = valid_contracts(clean).merge(clean["catalog"], on="product_id")
    change = config.PRICE_CHANGES["Microsoft"]
    ms = c[c["publisher"] == "Microsoft"]
    flagged = ms[(ms["start_date"] < change) & (ms["renewal_date"] >= change)]
    assert set(flagged["contract_id"]) == truth_refs(clean, "price_change_renewal")


def test_installs_truth_matches_the_definition(clean):
    c = valid_contracts(clean).drop(columns="site_id")
    c = c.merge(clean["owners"][["owner_id", "site_id"]], on="owner_id")
    ent = c.groupby(["product_id", "site_id"])["seats_purchased"].sum()
    inv = clean["inventory"].dropna(subset=["_product_id"])
    latest = inv[inv["scan_date"] == inv["scan_date"].max()]
    installs = latest.groupby(["_product_id", "site_id"])["installs"].sum()
    joined = pd.concat([ent.rename("ent"), installs.rename("inst")], axis=1).dropna()
    over = {f"{p}|{s}" for (p, s), r in joined.iterrows() if r["inst"] > r["ent"]}
    assert over == truth_refs(clean, "installs_over_entitlement")


def test_spike_truth_is_large_growth_and_decoys_are_moderate(clean):
    inv = clean["inventory"].dropna(subset=["_product_id"])
    totals = inv.groupby(["_product_id", "site_id", "scan_date"])["installs"].sum().unstack()
    growth = totals.iloc[:, -1] / totals.iloc[:, -2] - 1
    spikes = {f"{p}|{s}" for (p, s), g in growth.items() if g >= SPIKE_TRUE_GROWTH}
    assert spikes == truth_refs(clean, "usage_spike")


@pytest.fixture(scope="module")
def border():
    return generate_clean(scenario=scenarios.get_scenario("borderline"))


def test_borderline_has_contracts_on_both_sides_of_each_tier_edge(border):
    c = valid_contracts(border)
    days = set((c["renewal_date"].map(lambda d: (d - TODAY).days) - c["notice_days"]).tolist())
    assert {0, 30, 31, 60, 61, 90, 91, 92} <= days


def test_borderline_has_seats_idle_exactly_at_the_edge(border):
    age = border["usage"]["last_active_date"].map(lambda d: (TODAY - d).days)
    assert {89, 90, 91, 92} <= set(age.tolist())


def test_borderline_has_installs_equal_to_just_under_and_just_over_entitlement(border):
    c = valid_contracts(border).drop(columns="site_id")
    c = c.merge(border["owners"][["owner_id", "site_id"]], on="owner_id")
    ent = c.groupby(["product_id", "site_id"])["seats_purchased"].sum()
    inv = border["inventory"].dropna(subset=["_product_id"])
    latest = inv[inv["scan_date"] == inv["scan_date"].max()]
    inst = latest.groupby(["_product_id", "site_id"])["installs"].sum()
    diff = (inst - ent).dropna()
    assert {-1, 0, 1} <= set(diff.astype(int).tolist())


def test_borderline_has_microsoft_contract_starting_exactly_on_the_change_date(border):
    c = valid_contracts(border).merge(border["catalog"], on="product_id")
    starts = set(c.loc[c["publisher"] == "Microsoft", "start_date"])
    change = config.PRICE_CHANGES["Microsoft"]
    assert {change, change - timedelta(days=1)} <= starts
