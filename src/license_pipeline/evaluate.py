"""Score rule output against injected ground truth and render the evaluation report."""

from pathlib import Path

import pandas as pd

from . import config

SCORE_COLUMNS = [
    "rule", "expected", "flagged", "tp", "fp", "fn",
    "precision", "recall", "false_positives", "missed",
]
MAX_LISTED = 8


def read_ground_truth(raw_dir: Path = config.RAW_DIR) -> pd.DataFrame:
    return pd.read_csv(raw_dir / "ground_truth.csv", dtype=str, keep_default_na=False)


def score(found: pd.DataFrame, truth: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Precision and recall per rule for one kind of truth (alert or dq)."""
    expected_rows = truth[truth["kind"] == kind]
    rows = []
    for rule in sorted(set(expected_rows["rule"])):
        expected = set(expected_rows.loc[expected_rows["rule"] == rule, "record_ref"])
        got = set(found.loc[found["rule"] == rule, "record_ref"])
        tp, fp, fn = len(expected & got), len(got - expected), len(expected - got)
        rows.append(
            {
                "rule": rule,
                "expected": len(expected),
                "flagged": len(got),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": tp / (tp + fp) if tp + fp else float("nan"),
                "recall": tp / (tp + fn) if expected else float("nan"),
                "false_positives": sorted(got - expected),
                "missed": sorted(expected - got),
            }
        )
    return pd.DataFrame(rows, columns=SCORE_COLUMNS)


def _pct(value: float) -> str:
    return "n/a" if value != value else f"{value:.1%}"


def _table(scores: pd.DataFrame) -> list[str]:
    lines = [
        "| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.rule} | {r.expected} | {r.flagged} | {r.tp} | {r.fp} | {r.fn} | "
        f"{_pct(r.precision)} | {_pct(r.recall)} |"
        for r in scores.itertuples()
    ]
    return lines


def _mismatches(*score_tables: pd.DataFrame) -> list[str]:
    lines = []
    for r in pd.concat(score_tables).itertuples():
        for label, refs in (("False positives", r.false_positives), ("Missed", r.missed)):
            if refs:
                shown = ", ".join(refs[:MAX_LISTED]) + (" ..." if len(refs) > MAX_LISTED else "")
                lines.append(f"- `{r.rule}` {label.lower()} ({len(refs)}): {shown}")
    return lines or ["- None"]


def render_report(
    alert_scores: pd.DataFrame, dq_scores: pd.DataFrame, counts: dict[str, int]
) -> str:
    lines = [
        "# Evaluation report",
        "",
        "All data is synthetic. Results show how well the rules recover cases injected by the "
        "generator (seed fixed). They are not a measure of accuracy on real data.",
        "",
        "Injected cases sit well clear of every threshold, so a perfect score here shows the "
        "rules are implemented as specified. It does not show they would hold up on borderline "
        "real-world cases.",
        "",
        "## Record counts",
        "",
        "| Table | Rows |",
        "|---|---|",
        *[f"| {name} | {n} |" for name, n in counts.items()],
        "",
        "## Alert rules: precision and recall",
        "",
        *_table(alert_scores),
        "",
        "## Data quality checks: precision and recall",
        "",
        *_table(dq_scores),
        "",
        "## Mismatches",
        "",
        *_mismatches(alert_scores, dq_scores),
        "",
    ]
    return "\n".join(lines)


def write_report(text: str, out_dir: Path = config.REPORT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "eval_report.md"
    path.write_text(text)
    return path


def main(raw_dir: Path = config.RAW_DIR, report_dir: Path = config.REPORT_DIR) -> Path:
    """Generate raw data, run the pipeline, score it, and write the report."""
    from .generate import generate, write_raw
    from .pipeline import run_pipeline

    write_raw(generate(), raw_dir)
    result = run_pipeline(raw_dir)
    truth = read_ground_truth(raw_dir)
    counts = {
        **dict(zip(result["raw_counts"]["table"], result["raw_counts"]["rows"], strict=True)),
        "contracts after quarantine": len(result["fact_contract"]),
        "dq_issue rows": len(result["dq_issue"]),
        "alert rows": len(result["alert"]),
    }
    text = render_report(
        score(result["alert"], truth, "alert"), score(result["dq_issue"], truth, "dq"), counts
    )
    return write_report(text, report_dir)


if __name__ == "__main__":
    print(main())
