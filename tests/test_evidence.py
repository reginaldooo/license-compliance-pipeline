import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from license_pipeline import evidence

NOW = datetime(2026, 11, 25, 9, 0, tzinfo=UTC)


def run(created, event="schedule", conclusion="success", n=1):
    return {
        "createdAt": created, "event": event, "conclusion": conclusion, "status": "completed",
        "url": f"https://github.com/o/r/actions/runs/{n}",
    }


def test_recent_runs_keeps_last_seven_days_newest_first():
    runs = [
        run("2026-11-18T08:59:59Z", n=1),
        run("2026-11-18T09:00:00Z", n=2),
        run("2026-11-24T02:00:00Z", n=3),
        run("2026-11-21T02:00:00Z", n=4),
    ]
    kept = evidence.recent_runs(runs, NOW)
    assert [r["url"][-1] for r in kept] == ["3", "4", "2"]


def test_render_table_labels_trigger_result_and_links():
    table = evidence.render_table(
        [run("2026-11-24T02:00:00Z", "schedule", "success", 7),
         run("2026-11-23T09:41:00Z", "workflow_dispatch", "failure", 8)]
    )
    link = "[run](https://github.com/o/r/actions/runs/7)"
    assert f"| 2026-11-24 02:00 | scheduled | success | {link} |" in table
    assert "| 2026-11-23 09:41 | manual | failure |" in table


def test_summary_counts_triggers_and_outcomes():
    runs = [
        run("2026-11-24T02:00:00Z", "schedule", "success", 1),
        run("2026-11-24T07:00:00Z", "schedule", "failure", 2),
        run("2026-11-23T09:00:00Z", "workflow_dispatch", "success", 3),
    ]
    expected = "3 runs in the last 7 days: 2 scheduled, 1 manual; 2 succeeded, 1 failed."
    assert expected in evidence.render_table(runs)


def test_in_progress_run_is_not_counted_as_success_or_failure():
    pending = {**run("2026-11-24T02:00:00Z"), "conclusion": "", "status": "in_progress"}
    table = evidence.render_table([pending])
    assert "in progress" in table
    assert "0 succeeded, 0 failed" in table


def test_empty_table_says_no_runs():
    assert "No runs in the last 7 days." in evidence.render_table([])


def test_replace_block_swaps_only_between_markers_and_is_idempotent():
    text = f"intro\n{evidence.RUNS_START}\nold\n{evidence.RUNS_END}\noutro\n"
    once = evidence.replace_block(text, "new table")
    assert once == f"intro\n{evidence.RUNS_START}\nnew table\n{evidence.RUNS_END}\noutro\n"
    assert evidence.replace_block(once, "new table") == once


def test_replace_block_requires_markers():
    with pytest.raises(ValueError, match="markers"):
        evidence.replace_block("no markers here", "x")


def test_fetch_runs_calls_gh_and_parses_json():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(stdout=json.dumps([run("2026-11-24T02:00:00Z")]), returncode=0)

    runs = evidence.fetch_runs("daily-digest.yml", fake_run)
    assert runs[0]["event"] == "schedule"
    assert calls[0][:3] == ["gh", "run", "list"] and "daily-digest.yml" in calls[0]


def test_update_file_writes_and_reports_change(tmp_path):
    path = tmp_path / "EVIDENCE.md"
    path.write_text(f"{evidence.RUNS_START}\n{evidence.RUNS_END}\n")
    runs = [run("2026-11-24T02:00:00Z")]
    assert evidence.update_file(path, runs, NOW) is True
    assert "scheduled" in path.read_text()
    assert evidence.update_file(path, runs, NOW) is False


def test_main_updates_file_using_gh(tmp_path, monkeypatch):
    path = tmp_path / "EVIDENCE.md"
    path.write_text(f"{evidence.RUNS_START}\n{evidence.RUNS_END}\n")
    fake = [run("2026-11-24T02:00:00Z")]
    monkeypatch.setattr(evidence, "fetch_runs", lambda workflow, runner=None: fake)
    monkeypatch.setattr(evidence, "_now", lambda: NOW)
    assert evidence.main([str(path)]) == 0
    assert "2026-11-24 02:00" in path.read_text()


def test_repository_evidence_file_has_the_markers():
    path = Path(__file__).resolve().parents[1] / "docs" / "EVIDENCE.md"
    text = path.read_text()
    assert evidence.RUNS_START in text and evidence.RUNS_END in text
    assert evidence.replace_block(text, "x").count("x") >= 1
