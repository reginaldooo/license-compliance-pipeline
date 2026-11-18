from datetime import date, timedelta

import pandas as pd

from license_pipeline import alerts

TODAY = date(2026, 11, 18)


def contract(cid="C1", product="P001", owner="O1", seats=10, start=None, renewal=None, notice=30):
    return {
        "contract_id": cid, "product_id": product, "owner_id": owner,
        "seats_purchased": seats, "start_date": start or date(2026, 1, 1),
        "renewal_date": renewal or TODAY + timedelta(days=400), "notice_days": notice,
    }


def contracts_for_days_to_notice(*days, notice=30):
    return pd.DataFrame(
        [
            contract(f"C{i}", renewal=TODAY + timedelta(days=d + notice), notice=notice)
            for i, d in enumerate(days)
        ]
    )


def rules(df):
    return dict(zip(df["record_ref"], df["rule"], strict=True))


def test_renewal_tiers_use_notice_deadline():
    c = contracts_for_days_to_notice(20, 45, 85, 120)
    assert rules(alerts.renewal_alerts(c, TODAY)) == {
        "C0": "renewal_30", "C1": "renewal_60", "C2": "renewal_90",
    }


def test_renewal_window_edges_are_inclusive():
    c = contracts_for_days_to_notice(30, 31, 60, 90, 91)
    got = rules(alerts.renewal_alerts(c, TODAY))
    assert got == {"C0": "renewal_30", "C1": "renewal_60", "C2": "renewal_60", "C3": "renewal_90"}


def test_missed_notice_deadline_is_high_severity_tier_30():
    out = alerts.renewal_alerts(contracts_for_days_to_notice(-5), TODAY)
    assert out["rule"].tolist() == ["renewal_30"]
    assert out["severity"].tolist() == ["high"]
    assert "passed" in out["message"].iloc[0]


def owners():
    return pd.DataFrame({"owner_id": ["O1"], "site_id": ["S1"]})


def inv(rows):
    return pd.DataFrame(
        [
            {"product_id": p, "site_id": s, "scan_date": d, "installs": n}
            for p, s, d, n in rows
        ]
    )


def test_installs_over_entitlement_compares_latest_scan_to_summed_seats():
    c = pd.DataFrame([contract("C1", seats=6), contract("C2", seats=4)])
    old, new = TODAY - timedelta(days=30), TODAY
    inventory = inv([("P001", "S1", old, 50), ("P001", "S1", new, 6), ("P001", "S1", new, 5)])
    out = alerts.installs_over_entitlement(c, owners(), inventory)
    assert out["record_ref"].tolist() == ["P001|S1"]
    assert "11" in out["message"].iloc[0]


def test_installs_at_entitlement_or_without_contract_not_flagged():
    c = pd.DataFrame([contract("C1", seats=10)])
    inventory = inv([("P001", "S1", TODAY, 10), ("P002", "S1", TODAY, 99)])
    assert alerts.installs_over_entitlement(c, owners(), inventory).empty


def test_unused_seat_boundary_is_strictly_more_than_90_days():
    usage = pd.DataFrame(
        {
            "seat_id": ["A", "B", "C"],
            "product_id": ["P001"] * 3,
            "last_active_date": [
                TODAY - timedelta(days=90), TODAY - timedelta(days=91), TODAY,
            ],
        }
    )
    ai = pd.DataFrame(
        {"seat_id": ["AI-1"], "product_id": ["P016"], "last_active_date": [TODAY - timedelta(200)]}
    )
    out = alerts.unused_seats(usage, ai, TODAY)
    assert set(out["record_ref"]) == {"B", "AI-1"}


def test_usage_spike_flags_only_outlier_growth():
    rows = []
    for i in range(12):
        rows += [
            (f"P{i}", "S1", TODAY - timedelta(30), 100),
            (f"P{i}", "S1", TODAY, 100 + (i % 5) * 2),
        ]
    rows += [("PX", "S1", TODAY - timedelta(30), 100), ("PX", "S1", TODAY, 300)]
    assert alerts.usage_spikes(inv(rows))["record_ref"].tolist() == ["PX|S1"]


def test_usage_spike_needs_two_scans_and_enough_combos():
    assert alerts.usage_spikes(inv([("P1", "S1", TODAY, 10)])).empty


def catalog():
    return pd.DataFrame(
        {"product_id": ["P001", "P004"], "publisher": ["Microsoft", "Adobe"]}
    )


def test_price_change_flags_contracts_spanning_the_change_date():
    c = pd.DataFrame(
        [
            contract("C1", start=date(2025, 9, 1), renewal=date(2027, 9, 1)),
            contract("C2", start=date(2026, 8, 1), renewal=date(2027, 8, 1)),
            contract("C3", product="P004", start=date(2025, 9, 1), renewal=date(2027, 9, 1)),
        ]
    )
    assert alerts.price_change_renewals(c, catalog())["record_ref"].tolist() == ["C1"]


def test_run_alerts_returns_standard_columns():
    c = contracts_for_days_to_notice(20)
    inventory = pd.DataFrame(columns=["product_id", "site_id", "scan_date", "installs"])
    seats = pd.DataFrame(columns=["seat_id", "product_id", "last_active_date"])
    out = alerts.run_alerts(c, owners(), catalog(), inventory, seats, seats, TODAY)
    assert list(out.columns) == alerts.ALERT_COLUMNS
    assert set(out["rule"]) == {"renewal_30", "price_change_renewal"}
