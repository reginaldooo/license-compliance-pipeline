from datetime import date

import pandas as pd
import pytest

from license_pipeline import config, quality, scenarios
from license_pipeline.generate import generate_clean

TODAY = date(2026, 11, 18)


def contract(cid="C1", **over):
    row = {
        "contract_id": cid, "product_id": "P001", "owner_id": "O1", "seats_purchased": 10.0,
        "annual_cost": 100.0, "start_date": date(2026, 1, 1),
        "renewal_date": date(2027, 1, 1), "notice_days": 30.0,
    }
    return {**row, **over}


def frame(*rows):
    return pd.DataFrame(list(rows))


def refs(df, rule):
    return set(df.loc[df["rule"] == rule, "record_ref"])


def owners():
    return pd.DataFrame({"owner_id": ["O1", "O2"], "site_id": ["S1", "S2"]})


def test_identical_copies_are_duplicates_and_differing_copies_are_conflicts():
    c = frame(
        contract("C1"), contract("C1"),
        contract("C2"), contract("C2", seats_purchased=99.0),
        contract("C3"),
    )
    assert refs(quality.check_duplicates(c), "duplicate") == {"C1"}
    assert refs(quality.check_conflicting_duplicates(c), "conflicting_duplicate") == {"C2"}


def test_three_copies_with_one_different_are_a_conflict_not_a_duplicate():
    c = frame(contract("C1"), contract("C1"), contract("C1", renewal_date=date(2028, 1, 1)))
    assert refs(quality.check_duplicates(c), "duplicate") == set()
    assert refs(quality.check_conflicting_duplicates(c), "conflicting_duplicate") == {"C1"}


def test_expired_flags_valid_dates_in_the_past_only():
    c = frame(
        contract("C1", start_date=date(2025, 1, 1), renewal_date=date(2026, 11, 17)),
        contract("C2", renewal_date=TODAY),
        contract("C3", start_date=date(2027, 1, 1), renewal_date=date(2026, 6, 1)),  # invalid
        contract("C4", renewal_date=None),
    )
    assert refs(quality.check_expired(c, TODAY), "expired_contract") == {"C1"}


def test_unknown_owner_flags_nonblank_ids_missing_from_owners():
    c = frame(contract("C1", owner_id="O9"), contract("C2", owner_id=""), contract("C3"))
    assert refs(quality.check_unknown_owner(c, owners()), "unknown_owner") == {"C1"}


def test_quarantine_removes_conflicting_expired_and_unknown_owner_contracts():
    c = frame(
        contract("C1"), contract("C1", seats_purchased=5.0),
        contract("C2", start_date=date(2025, 1, 1), renewal_date=date(2026, 1, 1)),
        contract("C3", owner_id="O9"),
        contract("C4"), contract("C4"),
        contract("C5"),
    )
    assert quality.quarantine(c, owners(), TODAY)["contract_id"].tolist() == ["C4", "C5"]


def test_quarantine_without_owners_or_today_keeps_the_old_behavior():
    c = frame(contract("C3", owner_id="O9"), contract("C2", renewal_date=date(2026, 1, 2)))
    assert len(quality.quarantine(c)) == 2


def test_run_checks_reports_the_new_rules():
    c = frame(
        contract("C1"), contract("C1", seats_purchased=5.0),
        contract("C2", start_date=date(2025, 1, 1), renewal_date=date(2026, 1, 1)),
        contract("C3", owner_id="O9"),
    )
    inv = pd.DataFrame(
        {"row_id": ["I1"], "product_id": ["P001"], "site_id": ["S1"]}
    )
    out = quality.run_checks(c, owners(), inv, TODAY)
    assert {"conflicting_duplicate", "expired_contract", "unknown_owner"} <= set(out["rule"])


@pytest.fixture(scope="module")
def conflict():
    return generate_clean(scenario=scenarios.get_scenario("conflict"))


def test_conflict_scenario_is_registered():
    assert scenarios.get_scenario("conflict").conflicts is True


@pytest.mark.parametrize("rule", ["conflicting_duplicate", "expired_contract", "unknown_owner"])
def test_conflict_truth_has_n_cases_per_new_rule(conflict, rule):
    t = conflict["ground_truth"]
    assert (t["rule"] == rule).sum() == config.INJECT_PER_RULE


def test_conflict_truth_matches_the_generated_rows(conflict):
    c, t = conflict["contracts"], conflict["ground_truth"]

    def ids(rule):
        return set(t.loc[t["rule"] == rule, "record_ref"])

    for cid in ids("conflicting_duplicate"):
        copies = c[c["contract_id"] == cid]
        assert len(copies) == 2 and len(copies.drop_duplicates()) == 2
    expired = c[c["contract_id"].isin(ids("expired_contract"))]
    assert (expired["renewal_date"] < TODAY).all()
    assert (expired["renewal_date"] > expired["start_date"]).all()
    unknown = c[c["contract_id"].isin(ids("unknown_owner"))]
    assert not unknown["owner_id"].isin(conflict["owners"]["owner_id"]).any()
    assert (unknown["owner_id"] != "").all()


def test_baseline_has_no_conflicts():
    t = generate_clean()["ground_truth"]
    assert not t["rule"].isin(["conflicting_duplicate", "expired_contract", "unknown_owner"]).any()
