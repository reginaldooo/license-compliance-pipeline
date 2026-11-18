from datetime import date

import pandas as pd

from license_pipeline import load


class FakeJob:
    def result(self):
        return self


class FakeClient:
    def __init__(self):
        self.datasets = []
        self.loads = []

    def create_dataset(self, dataset_id, exists_ok=False):
        self.datasets.append((dataset_id, exists_ok))

    def load_table_from_dataframe(self, frame, table_id, job_config=None):
        self.loads.append((table_id, len(frame), job_config.write_disposition))
        return FakeJob()


def tables():
    return {
        "fact_contract": pd.DataFrame({"contract_id": ["C1"], "renewal_date": [date(2027, 1, 2)]}),
        "alert": pd.DataFrame({"rule": ["r"], "contract_id": [None]}),
        "pipeline_run_log": pd.DataFrame({"run_id": ["run-1"]}),
    }


def test_write_parquet_round_trips_dates_and_nulls(tmp_path):
    paths = load.write_parquet(tables(), tmp_path)
    assert {p.name for p in paths} == {
        "fact_contract.parquet", "alert.parquet", "pipeline_run_log.parquet",
    }
    back = pd.read_parquet(tmp_path / "fact_contract.parquet")
    assert back["renewal_date"].iloc[0] == date(2027, 1, 2)
    assert pd.read_parquet(tmp_path / "alert.parquet")["contract_id"].isna().all()


def test_bigquery_load_creates_dataset_and_uses_per_table_write_mode():
    client = FakeClient()
    ids = load.load_bigquery(tables(), "proj", "ds", client=client)
    assert client.datasets == [("proj.ds", True)]
    modes = {table_id: mode for table_id, _, mode in client.loads}
    assert modes["proj.ds.fact_contract"] == "WRITE_TRUNCATE"
    assert modes["proj.ds.alert"] == "WRITE_TRUNCATE"
    assert modes["proj.ds.pipeline_run_log"] == "WRITE_APPEND"
    assert set(ids) == set(modes)


def test_bigquery_load_skips_helper_tables():
    client = FakeClient()
    extra = {**tables(), "raw_counts": pd.DataFrame({"x": [1]})}
    load.load_bigquery(extra, "p", "d", client=client)
    assert all("raw_counts" not in table_id for table_id, _, _ in client.loads)
