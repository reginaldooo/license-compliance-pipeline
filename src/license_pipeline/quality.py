"""Data quality checks. Each check returns dq rows: rule, table, record_ref, severity."""

import pandas as pd

DQ_COLUMNS = ["rule", "table", "record_ref", "severity"]
ERROR = "error"
WARNING = "warning"


def _rows(rule: str, table: str, refs: list[str], severity: str) -> pd.DataFrame:
    unique = sorted(set(refs))
    return pd.DataFrame(
        {"rule": rule, "table": table, "record_ref": unique, "severity": severity},
        columns=DQ_COLUMNS,
    )


def _missing_owner_mask(contracts: pd.DataFrame) -> pd.Series:
    return contracts["owner_id"].fillna("").str.strip() == ""


def _invalid_date_mask(contracts: pd.DataFrame) -> pd.Series:
    bad = [
        s is None or r is None or r < s
        for s, r in zip(contracts["start_date"], contracts["renewal_date"], strict=True)
    ]
    return pd.Series(bad, index=contracts.index)


def _negative_seats_mask(contracts: pd.DataFrame) -> pd.Series:
    return contracts["seats_purchased"] < 0


def check_duplicates(contracts: pd.DataFrame) -> pd.DataFrame:
    repeated = contracts.loc[contracts["contract_id"].duplicated(keep=False), "contract_id"]
    return _rows("duplicate", "contracts", repeated.tolist(), ERROR)


def check_missing_owner(contracts: pd.DataFrame) -> pd.DataFrame:
    ids = contracts.loc[_missing_owner_mask(contracts), "contract_id"]
    return _rows("missing_owner", "contracts", ids.tolist(), ERROR)


def check_invalid_dates(contracts: pd.DataFrame) -> pd.DataFrame:
    ids = contracts.loc[_invalid_date_mask(contracts), "contract_id"]
    return _rows("invalid_date", "contracts", ids.tolist(), ERROR)


def check_negative_seats(contracts: pd.DataFrame) -> pd.DataFrame:
    ids = contracts.loc[_negative_seats_mask(contracts), "contract_id"]
    return _rows("negative_seats", "contracts", ids.tolist(), ERROR)


def check_unmapped_product(inventory: pd.DataFrame) -> pd.DataFrame:
    ids = inventory.loc[inventory["product_id"].isna(), "row_id"]
    return _rows("unmapped_product", "inventory", ids.tolist(), WARNING)


def check_contract_without_inventory(
    contracts: pd.DataFrame, owners: pd.DataFrame, inventory: pd.DataFrame
) -> pd.DataFrame:
    keys = set(zip(inventory["product_id"], inventory["site_id"], strict=True))
    sited = contracts.merge(owners[["owner_id", "site_id"]], on="owner_id")
    orphan = [
        (p, s) not in keys
        for p, s in zip(sited["product_id"], sited["site_id"], strict=True)
    ]
    ids = sited.loc[orphan, "contract_id"].tolist()
    return _rows("contract_without_inventory", "contracts", ids, WARNING)


def check_inventory_without_contract(
    inventory: pd.DataFrame, contracts: pd.DataFrame, owners: pd.DataFrame
) -> pd.DataFrame:
    sited = contracts.merge(owners[["owner_id", "site_id"]], on="owner_id")
    keys = set(zip(sited["product_id"], sited["site_id"], strict=True))
    mapped = inventory.dropna(subset=["product_id"])
    orphan = [
        (p, s) not in keys
        for p, s in zip(mapped["product_id"], mapped["site_id"], strict=True)
    ]
    ids = mapped.loc[orphan, "row_id"].tolist()
    return _rows("inventory_without_contract", "inventory", ids, WARNING)


def quarantine(contracts: pd.DataFrame) -> pd.DataFrame:
    """Drop contracts that fail a blocking check, then drop repeated contract ids."""
    bad = (
        _missing_owner_mask(contracts)
        | _invalid_date_mask(contracts)
        | _negative_seats_mask(contracts)
    )
    return contracts.loc[~bad].drop_duplicates("contract_id").reset_index(drop=True)


def run_checks(
    contracts: pd.DataFrame, owners: pd.DataFrame, inventory: pd.DataFrame
) -> pd.DataFrame:
    """Run blocking checks on raw contracts, then structural checks on the quarantined set."""
    valid = quarantine(contracts)
    mapped = inventory.dropna(subset=["product_id"])
    return pd.concat(
        [
            check_duplicates(contracts),
            check_missing_owner(contracts),
            check_invalid_dates(contracts),
            check_negative_seats(contracts),
            check_unmapped_product(inventory),
            check_contract_without_inventory(valid, owners, mapped),
            check_inventory_without_contract(inventory, valid, owners),
        ],
        ignore_index=True,
    )
