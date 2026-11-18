"""Write curated tables to local Parquet and, when configured, to BigQuery."""

from pathlib import Path

import pandas as pd

LOADABLE_TABLES = frozenset(
    {
        "dim_product", "dim_owner", "fact_contract", "fact_inventory", "fact_usage",
        "fact_ai_seat", "dq_issue", "alert", "pipeline_run_log",
    }
)
APPEND_TABLES = frozenset({"pipeline_run_log"})


def write_parquet(tables: dict[str, pd.DataFrame], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, table in tables.items():
        path = out_dir / f"{name}.parquet"
        table.to_parquet(path, index=False)
        paths.append(path)
    return paths


def load_bigquery(
    tables: dict[str, pd.DataFrame], project: str, dataset: str, client=None
) -> list[str]:
    """Load curated tables. Snapshot tables are replaced each run; the run log is appended."""
    from google.cloud import bigquery

    client = client or bigquery.Client(project=project)
    client.create_dataset(f"{project}.{dataset}", exists_ok=True)
    loaded = []
    for name, table in tables.items():
        if name not in LOADABLE_TABLES:
            continue
        disposition = "WRITE_APPEND" if name in APPEND_TABLES else "WRITE_TRUNCATE"
        table_id = f"{project}.{dataset}.{name}"
        extra = {}
        if name in APPEND_TABLES:
            extra["schema_update_options"] = [bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        job_config = bigquery.LoadJobConfig(write_disposition=disposition, **extra)
        client.load_table_from_dataframe(table, table_id, job_config=job_config).result()
        loaded.append(table_id)
    return loaded
