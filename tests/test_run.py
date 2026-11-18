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


def test_log_records_scenario_and_quality_metrics(tmp_path):
    result = run.run(
        raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", generate_data=True, clock=lambda: NOW
    )
    log = result["pipeline_run_log"].iloc[0]
    assert log["scenario"] == "baseline"
    assert log["alert_precision"] == 1.0 and log["alert_recall"] == 1.0
    assert log["dq_precision"] == 1.0 and log["dq_recall"] == 1.0


def test_log_has_blank_scenario_and_no_metrics_without_ground_truth(tmp_path):
    from license_pipeline.generate import generate, write_raw

    raw = generate()
    write_raw({k: v for k, v in raw.items() if k != "ground_truth"}, tmp_path / "raw")
    log = run.run(raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", clock=lambda: NOW)[
        "pipeline_run_log"
    ].iloc[0]
    assert log["scenario"] == "" and pd.isna(log["alert_precision"])


def test_scenario_and_seed_are_used_for_generation(tmp_path):
    from license_pipeline import scenarios

    result = run.run(
        raw_dir=tmp_path / "raw", out_dir=tmp_path / "out", generate_data=True,
        scenario=scenarios.get_scenario("scale"), seed=7, clock=lambda: NOW,
    )
    assert len(result["fact_usage"]) == scenarios.get_scenario("scale").n_usage_seats
    assert result["pipeline_run_log"]["scenario"].iloc[0] == "scale"


def test_main_random_scenario_is_picked_from_the_date(tmp_path, capsys):
    from datetime import date

    from license_pipeline import scenarios

    day = date(2026, 11, 19)
    argv = ["--local", "--generate", "--scenario", "random", "--today", day.isoformat(),
            "--raw-dir", str(tmp_path / "raw"), "--out-dir", str(tmp_path / "o")]
    assert run.main(argv) == 0
    assert f"scenario={scenarios.pick_scenario(day).name}" in capsys.readouterr().out


def test_main_writes_github_step_summary(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    argv = ["--local", "--generate", "--raw-dir", str(tmp_path / "raw"),
            "--out-dir", str(tmp_path / "o")]
    assert run.main(argv) == 0
    text = summary.read_text()
    assert "baseline" in text and "installs_over_entitlement" in text
