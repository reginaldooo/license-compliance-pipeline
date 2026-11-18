from datetime import UTC, date, datetime

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


def test_main_digest_dry_run_prints_subject_without_sending(tmp_path, capsys):
    argv = ["--local", "--generate", "--raw-dir", str(tmp_path / "raw"),
            "--out-dir", str(tmp_path / "o"), "--digest", "jakarta", "--dry-run", "--force"]
    assert run.main(argv) == 0
    out = capsys.readouterr().out
    assert "[License digest] Jakarta" in out


def test_main_digest_skips_outside_send_hour(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(run, "should_send", lambda site_id, now: False)
    argv = ["--local", "--generate", "--raw-dir", str(tmp_path / "raw"),
            "--out-dir", str(tmp_path / "o"), "--digest", "paris"]
    assert run.main(argv) == 0
    assert "skipped" in capsys.readouterr().out
    assert not (tmp_path / "o").exists()


def test_run_generates_data_for_the_given_day(tmp_path):
    result = run.run(
        raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", generate_data=True,
        today=date(2027, 2, 1), clock=lambda: NOW,
    )
    assert len(result["fact_contract"]) == 120


def test_deliver_digest_sends_with_env_settings(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setattr(run, "send_email", lambda *args: sent.append(args))
    monkeypatch.setenv("SMTP_USER", "me@x.test")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "pw")
    monkeypatch.setenv("DIGEST_TO", "you@x.test")
    result = run.run(
        raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", generate_data=True, clock=lambda: NOW
    )
    message = run.deliver_digest(result, "paris", date(2026, 11, 18), dry_run=False)
    assert "you@x.test" in message
    subject, _, _, to, settings = sent[0]
    assert subject.startswith("[License digest] Paris") and to == ["you@x.test"]
    assert settings.user == "me@x.test"
