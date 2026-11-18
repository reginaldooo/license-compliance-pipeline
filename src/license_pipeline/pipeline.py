"""Run every pipeline stage in memory: ingest, normalize, quality checks, alerts."""

from datetime import date
from pathlib import Path

import pandas as pd

from . import config
from .alerts import run_alerts
from .ingest import load_tables
from .normalize import normalize_inventory
from .quality import quarantine, run_checks


def run_pipeline(
    raw_dir: Path = config.RAW_DIR, today: date = config.TODAY
) -> dict[str, pd.DataFrame]:
    tables = load_tables(raw_dir)
    catalog = pd.read_csv(config.CATALOG_PATH)
    inventory = normalize_inventory(tables["inventory"], catalog)
    dq_issue = run_checks(tables["contracts"], tables["owners"], inventory)
    contracts = quarantine(tables["contracts"])
    alert = run_alerts(
        contracts, tables["owners"], catalog, inventory, tables["usage"], tables["ai_seats"], today
    )
    return {
        "dim_product": catalog,
        "dim_owner": tables["owners"],
        "fact_contract": contracts,
        "fact_inventory": inventory,
        "fact_usage": tables["usage"],
        "fact_ai_seat": tables["ai_seats"],
        "dq_issue": dq_issue,
        "alert": alert,
        "raw_counts": pd.DataFrame(
            {"table": list(tables), "rows": [len(t) for t in tables.values()]}
        ),
    }
