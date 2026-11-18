from datetime import date

import numpy as np
import pandas as pd
import pytest

from license_pipeline import config, quality, scenarios
from license_pipeline.generate import generate, generate_clean
from license_pipeline.ingest import parse_date
from license_pipeline.synth_noise import format_date, messy_name

NAME = "Microsoft 365 E3"


def test_messy_scenario_is_registered_and_flagged():
    assert scenarios.get_scenario("messy").messy is True


def test_harsh_names_are_more_varied_than_normal_names():
    rng_a, rng_b = np.random.default_rng(1), np.random.default_rng(1)
    normal = {messy_name("P001", NAME, rng_a) for _ in range(400)}
    harsh = {messy_name("P001", NAME, rng_b, harsh=True) for _ in range(400)}
    assert len(harsh) > len(normal)
    assert any(" " not in n.strip() for n in harsh)


def test_extra_date_formats_round_trip_through_the_parser():
    rng = np.random.default_rng(3)
    day = date(2027, 3, 9)
    seen = {format_date(day, rng, extra=True) for _ in range(200)}
    assert len(seen) >= 5
    assert {parse_date(s) for s in seen} == {day}


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Nov 18, 2026", date(2026, 11, 18)), ("2026/11/18", date(2026, 11, 18)),
     ("Feb 31, 2026", None), ("18-11-26", None)],
)
def test_parser_supports_extra_formats_and_rejects_the_rest(text, expected):
    assert parse_date(text) == expected


def contract(cid, **over):
    row = {
        "contract_id": cid, "product_id": "P001", "owner_id": "O1", "seats_purchased": 10.0,
        "annual_cost": 100.0, "start_date": date(2026, 1, 1),
        "renewal_date": date(2027, 1, 1), "notice_days": 30.0,
    }
    return {**row, **over}


def test_missing_value_check_flags_blank_seats_cost_or_notice():
    c = pd.DataFrame(
        [contract("C1", seats_purchased=np.nan), contract("C2", notice_days=np.nan),
         contract("C3", annual_cost=np.nan), contract("C4")]
    )
    out = quality.check_missing_values(c)
    assert set(out["record_ref"]) == {"C1", "C2", "C3"}
    assert set(out["rule"]) == {"missing_value"}


def test_quarantine_drops_rows_with_missing_values():
    c = pd.DataFrame([contract("C1", seats_purchased=np.nan), contract("C2")])
    assert quality.quarantine(c)["contract_id"].tolist() == ["C2"]


@pytest.fixture(scope="module")
def messy():
    return generate_clean(scenario=scenarios.get_scenario("messy"))


def test_messy_truth_includes_missing_values_and_more_unmapped_rows(messy):
    t = messy["ground_truth"]
    n = scenarios.get_scenario("messy").n_inject
    assert (t["rule"] == "missing_value").sum() == n
    assert (t["rule"] == "unmapped_product").sum() == 3 * n


def test_missing_value_truth_matches_blank_fields(messy):
    c = messy["contracts"]
    blank = c[c[["seats_purchased", "annual_cost", "notice_days"]].isna().any(axis=1)]
    t = messy["ground_truth"]
    assert set(blank["contract_id"]) == set(t.loc[t["rule"] == "missing_value", "record_ref"])


def test_match_truth_lists_every_mappable_inventory_row(messy):
    inv = messy["inventory"]
    mappable = inv[inv["_product_id"].notna()]
    t = messy["ground_truth"]
    pairs = zip(mappable["row_id"], mappable["_product_id"], strict=True)
    expected = {f"{r}->{p}" for r, p in pairs}
    assert expected == set(t.loc[t["rule"] == "name_match", "record_ref"])
    assert (t.loc[t["rule"] == "name_match", "kind"] == "match").all()


def test_messy_raw_contracts_have_blank_cells_and_extra_date_styles():
    raw = generate(scenario=scenarios.get_scenario("messy"))["contracts"]
    blanks = raw[["seats_purchased", "notice_days", "annual_cost"]].isna().any(axis=1)
    assert blanks.sum() >= 1
    starts = raw["start_date"].astype(str)
    assert starts.str.match(r"^\d{4}/\d{2}/\d{2}$").any()
    assert starts.str.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}$").any()


def test_baseline_has_no_missing_values_or_match_surprises():
    t = generate_clean()["ground_truth"]
    assert (t["rule"] == "missing_value").sum() == 0
    assert config.INJECT_PER_RULE == (t["rule"] == "unmapped_product").sum()
