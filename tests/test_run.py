from datetime import UTC, datetime

import pandas as pd
import pytest

from license_pipeline import run

NOW = datetime(2026, 11, 18, 2, 0, tzinfo=UTC)


def test_run_writes_parquet_and_success_log(tmp_path):
    result = run.run(
        raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", generate_data=True, clock=lambda: NOW
    )
    log = result["pipeline_run_log"].iloc[0]
    assert log["status"] == "success"
    assert log["run_id"] == "run-20261118T020000Z"
    assert log["rows_in"] > 0 and log["issues"] == len(result["dq_issue"])
    assert (tmp_path / "out" / "alert.parquet").exists()
    assert (tmp_path / "out" / "pipeline_run_log.parquet").exists()


def test_alert_and_dq_rows_are_stamped_with_run_id(tmp_path):
    result = run.run(
        raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", generate_data=True, clock=lambda: NOW
    )
    run_id = result["pipeline_run_log"]["run_id"].iloc[0]
    assert (result["alert"]["run_id"] == run_id).all()
    assert (result["dq_issue"]["run_id"] == run_id).all()
    assert result["alert"]["raised_at"].notna().all()


def test_failed_run_records_failed_log_and_reraises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run.run(raw_dir=tmp_path / "missing", out_dir=tmp_path / "out", clock=lambda: NOW)
    log = pd.read_parquet(tmp_path / "out" / "pipeline_run_log.parquet").iloc[0]
    assert log["status"] == "failed"
    assert "missing" in log["error"] or "No such file" in log["error"]


def test_bigquery_used_only_with_project_and_not_local(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(run, "load_bigquery", lambda tables, proj, dataset: calls.append(proj))
    run.run(raw_dir=tmp_path / "r1", out_dir=tmp_path / "o1", generate_data=True, clock=lambda: NOW)
    run.run(
        raw_dir=tmp_path / "r2", out_dir=tmp_path / "o2", generate_data=True,
        project="proj", local_only=True, clock=lambda: NOW,
    )
    assert calls == []
    run.run(
        raw_dir=tmp_path / "r3", out_dir=tmp_path / "o3", generate_data=True,
        project="proj", clock=lambda: NOW,
    )
    assert calls == ["proj"]


def test_main_local_generate(tmp_path, capsys):
    argv = ["--local", "--generate", "--raw-dir", str(tmp_path / "raw")]
    code = run.main([*argv, "--out-dir", str(tmp_path / "o")])
    assert code == 0
    assert "success" in capsys.readouterr().out
