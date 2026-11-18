"""Score rule output against injected ground truth and render the evaluation report."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import config
from .scenarios import SCENARIOS, Scenario

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
    for rule in sorted(set(expected_rows["rule"]) | set(found["rule"])):
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


def match_found(inventory: pd.DataFrame) -> pd.DataFrame:
    """Name-match output in the same shape as alerts: one row per inventory row that was mapped."""
    mapped = inventory.dropna(subset=["product_id"])
    refs = [f"{r}->{p}" for r, p in zip(mapped["row_id"], mapped["product_id"], strict=True)]
    return pd.DataFrame({"rule": "name_match", "record_ref": refs}, columns=["rule", "record_ref"])


def overall(scores: pd.DataFrame) -> tuple[float, float]:
    """Micro-averaged (precision, recall) across all rules in a score table."""
    tp, fp, fn = scores["tp"].sum(), scores["fp"].sum(), scores["fn"].sum()
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    return float(precision), float(recall)


def render_summary(
    scenario_name: str,
    alert_scores: pd.DataFrame,
    dq_scores: pd.DataFrame,
    match_scores: pd.DataFrame | None = None,
) -> str:
    """Short markdown block for the GitHub Actions run page."""
    ap, ar = overall(alert_scores)
    dp, dr = overall(dq_scores)
    lines = [
        f"## Evaluation: scenario `{scenario_name}`",
        "",
        f"Alert rules: precision {_pct(ap)}, recall {_pct(ar)}. "
        f"Data quality checks: precision {_pct(dp)}, recall {_pct(dr)}.",
    ]
    if match_scores is not None:
        mp, mr = overall(match_scores)
        lines += [f"Product name matching: precision {_pct(mp)}, recall {_pct(mr)}."]
    lines += ["", *_table(alert_scores), "", *_table(dq_scores), ""]
    return "\n".join(lines)


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


def write_report(text: str, out_dir: Path = config.REPORT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "eval_report.md"
    path.write_text(text)
    return path


DEFAULT_SEEDS = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    description: str
    counts: dict[str, int]
    alert: pd.DataFrame
    dq: pd.DataFrame
    match: pd.DataFrame


def aggregate(tables: list[pd.DataFrame]) -> pd.DataFrame:
    """Sum counts per rule across seeds and recompute precision and recall."""
    rows = []
    for rule, group in pd.concat(tables, ignore_index=True).groupby("rule", sort=True):
        tp, fp, fn = int(group["tp"].sum()), int(group["fp"].sum()), int(group["fn"].sum())
        rows.append(
            {
                "rule": rule,
                "expected": int(group["expected"].sum()),
                "flagged": int(group["flagged"].sum()),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": tp / (tp + fp) if tp + fp else float("nan"),
                "recall": tp / (tp + fn) if tp + fn else float("nan"),
                "false_positives": sorted({r for refs in group["false_positives"] for r in refs}),
                "missed": sorted({r for refs in group["missed"] for r in refs}),
            }
        )
    return pd.DataFrame(rows, columns=SCORE_COLUMNS)


def _score_run(scenario: Scenario, seed: int, work_dir: Path):
    from .generate import generate, write_raw
    from .pipeline import run_pipeline

    raw_dir = work_dir / f"{scenario.name}-{seed}"
    write_raw(generate(seed, config.TODAY, scenario), raw_dir)
    result = run_pipeline(raw_dir, config.TODAY)
    truth = read_ground_truth(raw_dir)
    counts = {
        **dict(zip(result["raw_counts"]["table"], result["raw_counts"]["rows"], strict=True)),
        "contracts after quarantine": len(result["fact_contract"]),
        "dq_issue rows": len(result["dq_issue"]),
        "alert rows": len(result["alert"]),
    }
    return (
        counts,
        score(result["alert"], truth, "alert"),
        score(result["dq_issue"], truth, "dq"),
        score(match_found(result["fact_inventory"]), truth, "match"),
    )


def evaluate_all(seeds: tuple[int, ...], work_dir: Path) -> list[ScenarioResult]:
    results = []
    for scenario in SCENARIOS.values():
        runs = [_score_run(scenario, seed, work_dir) for seed in seeds]
        results.append(
            ScenarioResult(
                scenario.name,
                scenario.description,
                runs[0][0],
                aggregate([r[1] for r in runs]),
                aggregate([r[2] for r in runs]),
                aggregate([r[3] for r in runs]),
            )
        )
    return results


def render_full_report(results: list[ScenarioResult], seeds: int) -> str:
    lines = [
        "# Evaluation report",
        "",
        "All data is synthetic. Results show how well the rules recover cases injected by the "
        f"generator, summed over {seeds} seeds per scenario. They are not a measure of accuracy "
        "on real data.",
        "",
        "Labels come from the generator and follow the rule definitions in the README, written "
        "separately from the rule code. Scenarios other than `baseline` add borderline cases, "
        "messier data, conflicts, or more volume, and are where mismatches show up.",
        "",
        "## Summary",
        "",
        "| Scenario | Alert precision | Alert recall | DQ precision | DQ recall "
        "| Name match precision | Name match recall |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        cells = [*overall(r.alert), *overall(r.dq), *overall(r.match)]
        lines.append(f"| {r.name} | " + " | ".join(_pct(c) for c in cells) + " |")
    for r in results:
        lines += [
            "",
            f"## Scenario: {r.name}",
            "",
            r.description,
            "",
            "| Table (first seed) | Rows |",
            "|---|---|",
            *[f"| {name} | {n} |" for name, n in r.counts.items()],
            "",
            "### Alert rules",
            "",
            *_table(r.alert),
            "",
            "### Data quality checks",
            "",
            *_table(r.dq),
            "",
            "### Product name matching",
            "",
            *_table(r.match),
            "",
            "### Mismatches",
            "",
            *_mismatches(r.alert, r.dq, r.match),
        ]
    return "\n".join(lines) + "\n"


def main(
    work_dir: Path | None = None,
    report_dir: Path = config.REPORT_DIR,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
) -> Path:
    """Score every scenario over several seeds and write the report."""
    if work_dir is None:
        with tempfile.TemporaryDirectory() as tmp:
            results = evaluate_all(seeds, Path(tmp))
    else:
        results = evaluate_all(seeds, work_dir)
    return write_report(render_full_report(results, len(seeds)), report_dir)


if __name__ == "__main__":
    print(main())
