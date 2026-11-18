"""Keep a rolling seven-day table of scheduled workflow runs inside docs/EVIDENCE.md.

Uses only the standard library and the GitHub CLI, so it runs on a bare Actions runner.
"""

import json
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

RUNS_START = "<!-- runs:start -->"
RUNS_END = "<!-- runs:end -->"
KEEP_DAYS = 7
WORKFLOW = "daily-digest.yml"
DEFAULT_PATH = Path("docs/EVIDENCE.md")
TRIGGER_LABELS = {"schedule": "scheduled", "workflow_dispatch": "manual"}


def _now() -> datetime:
    return datetime.now(UTC)


def _created(run: dict) -> datetime:
    return datetime.fromisoformat(run["createdAt"])


def recent_runs(runs: list[dict], now: datetime, keep_days: int = KEEP_DAYS) -> list[dict]:
    cutoff = now - timedelta(days=keep_days)
    kept = [r for r in runs if _created(r) >= cutoff]
    return sorted(kept, key=_created, reverse=True)


def _result(run: dict) -> str:
    return run["conclusion"] or "in progress"


def render_table(runs: list[dict]) -> str:
    if not runs:
        return f"No runs in the last {KEEP_DAYS} days."
    trigger = [TRIGGER_LABELS.get(r["event"], r["event"]) for r in runs]
    ok = sum(r["conclusion"] == "success" for r in runs)
    bad = sum(r["conclusion"] == "failure" for r in runs)
    summary = (
        f"{len(runs)} runs in the last {KEEP_DAYS} days: {trigger.count('scheduled')} scheduled, "
        f"{trigger.count('manual')} manual; {ok} succeeded, {bad} failed."
    )
    rows = [
        f"| {_created(r):%Y-%m-%d %H:%M} | {label} | {_result(r)} | [run]({r['url']}) |"
        for r, label in zip(runs, trigger, strict=True)
    ]
    header = ["| Run time (UTC) | Trigger | Result | Link |", "|---|---|---|---|"]
    return "\n".join([summary, "", *header, *rows])


def replace_block(text: str, block: str) -> str:
    start, end = text.find(RUNS_START), text.find(RUNS_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"expected the markers {RUNS_START} and {RUNS_END} in the file")
    return f"{text[: start + len(RUNS_START)]}\n{block}\n{text[end:]}"


def fetch_runs(workflow: str, runner: Callable = subprocess.run) -> list[dict]:
    command = [
        "gh", "run", "list", "--workflow", workflow, "--limit", "100",
        "--json", "createdAt,event,conclusion,status,url",
    ]
    done = runner(command, check=True, capture_output=True, text=True)
    return json.loads(done.stdout)


def update_file(path: Path, runs: list[dict], now: datetime) -> bool:
    """Rewrite the runs block. Returns True when the file content changed."""
    old = path.read_text()
    new = replace_block(old, render_table(recent_runs(runs, now)))
    if new == old:
        return False
    path.write_text(new)
    return True


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else DEFAULT_PATH
    changed = update_file(path, fetch_runs(WORKFLOW), _now())
    print(f"{path}: {'updated' if changed else 'unchanged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
