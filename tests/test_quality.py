from datetime import date

import pandas as pd
import pytest

from license_pipeline import config, quality
from license_pipeline.generate import generate, generate_clean, write_raw
from license_pipeline.ingest import load_tables
from license_pipeline.normalize import normalize_inventory


def contract(cid="C1", owner="O1", seats=10, start=date(2026, 1, 1), renewal=date(2027, 1, 1)):
    return {
        "contract_id": cid, "product_id": "P001", "owner_id": owner,
        "seats_purchased": seats, "annual_cost": 100, "start_date": start,
        "renewal_date": renewal, "notice_days": 30,
    }


def frame(*rows):
    return pd.DataFrame(list(rows))


def refs(df, rule):
    return set(df.loc[df["rule"] == rule, "record_ref"])


def test_duplicates_flag_repeated_contract_id():
    c = frame(contract("C1"), contract("C1"), contract("C2"))
    assert refs(quality.check_duplicates(c), "duplicate") == {"C1"}


def test_missing_owner_flags_blank_and_whitespace():
    c = frame(contract("C1", owner=""), contract("C2", owner="  "), contract("C3"))
    assert refs(quality.check_missing_owner(c), "missing_owner") == {"C1", "C2"}


def test_invalid_date_flags_none_and_renewal_before_start():
    c = frame(
        contract("C1", renewal=None),
        contract("C2", start=date(2027, 1, 1), renewal=date(2026, 1, 1)),
        contract("C3"),
    )
    assert refs(quality.check_invalid_dates(c), "invalid_date") == {"C1", "C2"}


def test_negative_seats_flags_below_zero_only():
    c = frame(contract("C1", seats=-5), contract("C2", seats=0), contract("C3"))
    assert refs(quality.check_negative_seats(c), "negative_seats") == {"C1"}


def test_unmapped_product_flags_rows_without_product_id():
    inv = pd.DataFrame({"row_id": ["I1", "I2"], "product_id": ["P001", None]})
    assert refs(quality.check_unmapped_product(inv), "unmapped_product") == {"I2"}


def test_quarantine_drops_bad_rows_and_dedupes():
    c = frame(
        contract("C1"), contract("C1"), contract("C2", owner=""),
        contract("C3", seats=-1), contract("C4", renewal=None), contract("C5"),
    )
    assert quality.quarantine(c)["contract_id"].tolist() == ["C1", "C5"]


def test_structural_checks_compare_product_site_keys():
    owners = pd.DataFrame({"owner_id": ["O1"], "site_id": ["S1"]})
    contracts = frame(contract("C1"), {**contract("C2"), "product_id": "P002"})
    inventory = pd.DataFrame(
        {
            "row_id": ["I1", "I2"],
            "product_id": ["P001", "P003"],
            "site_id": ["S1", "S1"],
        }
    )
    no_inv = quality.check_contract_without_inventory(contracts, owners, inventory)
    no_con = quality.check_inventory_without_contract(inventory, contracts, owners)
    assert refs(no_inv, "contract_without_inventory") == {"C2"}
    assert refs(no_con, "inventory_without_contract") == {"I2"}


def test_dq_rows_have_expected_columns():
    out = quality.check_negative_seats(frame(contract("C1", seats=-1)))
    assert list(out.columns) == ["rule", "table", "record_ref", "severity"]


@pytest.fixture(scope="module")
def pipeline_dq(tmp_path_factory):
    path = tmp_path_factory.mktemp("raw")
    write_raw(generate(), path)
    tables = load_tables(path)
    catalog = pd.read_csv(config.CATALOG_PATH)
    inventory = normalize_inventory(tables["inventory"], catalog)
    dq = quality.run_checks(tables["contracts"], tables["owners"], inventory)
    return dq, tables


DQ_RULES = [
    "duplicate", "missing_owner", "invalid_date", "negative_seats", "unmapped_product",
    "contract_without_inventory", "inventory_without_contract",
]


@pytest.mark.parametrize("rule", DQ_RULES)
def test_dq_matches_ground_truth_exactly(pipeline_dq, rule):
    dq, _ = pipeline_dq
    truth = generate_clean()["ground_truth"]
    expected = set(truth.loc[truth["rule"] == rule, "record_ref"])
    assert refs(dq, rule) == expected


def test_quarantine_leaves_exactly_the_base_contracts(pipeline_dq):
    _, tables = pipeline_dq
    clean = quality.quarantine(tables["contracts"])
    assert len(clean) == config.N_CONTRACTS
    assert clean["contract_id"].max() == f"C{config.N_CONTRACTS:04d}"
