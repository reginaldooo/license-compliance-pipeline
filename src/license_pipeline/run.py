"""Command-line entry point: generate (optional), run the pipeline, load, and log the run."""

import argparse
import os
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from . import config
from .digest import SmtpSettings, build_digest, recipients, send_email, should_send
from .generate import generate, write_raw
from .load import load_bigquery, write_parquet
from .pipeline import run_pipeline

DEFAULT_DATASET = "license_compliance"
FACT_TABLES = ("fact_contract", "fact_inventory", "fact_usage", "fact_ai_seat")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _log_row(
    run_id: str, started: datetime, finished: datetime, rows_in: int, rows_out: int,
    issues: int, status: str, error: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "run_id": run_id, "started_at": started, "finished_at": finished,
                "rows_in": rows_in, "rows_out": rows_out, "issues": issues,
                "status": status, "error": error,
            }
        ]
    )


def _run_id_first(table: pd.DataFrame) -> pd.DataFrame:
    return table[["run_id", *[c for c in table.columns if c != "run_id"]]]


def _stamp(tables: dict[str, pd.DataFrame], run_id: str, raised_at: datetime) -> dict:
    alert = tables["alert"].assign(run_id=run_id, raised_at=raised_at)
    dq_issue = tables["dq_issue"].assign(run_id=run_id)
    return {**tables, "alert": _run_id_first(alert), "dq_issue": _run_id_first(dq_issue)}


def run(
    raw_dir: Path = config.RAW_DIR,
    out_dir: Path = config.CURATED_DIR,
    today: date = config.TODAY,
    generate_data: bool = False,
    project: str | None = None,
    dataset: str = DEFAULT_DATASET,
    local_only: bool = False,
    clock: Callable[[], datetime] = _utc_now,
) -> dict[str, pd.DataFrame]:
    started = clock()
    run_id = f"run-{started:%Y%m%dT%H%M%SZ}"
    try:
        if generate_data:
            write_raw(generate(today=today), raw_dir)
        tables = run_pipeline(raw_dir, today)
        stamped = _stamp(tables, run_id, started)
        log = _log_row(
            run_id, started, clock(),
            rows_in=int(tables["raw_counts"]["rows"].sum()),
            rows_out=sum(len(tables[name]) for name in FACT_TABLES),
            issues=len(tables["dq_issue"]), status="success", error="",
        )
        result = {k: v for k, v in stamped.items() if k != "raw_counts"}
        result["pipeline_run_log"] = log
        write_parquet(result, out_dir)
        if project and not local_only:
            load_bigquery(result, project, dataset)
        return result
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        failed = _log_row(run_id, started, clock(), 0, 0, 0, "failed", error)
        write_parquet({"pipeline_run_log": failed}, out_dir)
        raise


def _site_id(name: str) -> str:
    return next(sid for sid, (site, _) in config.SITES.items() if site.lower() == name)


def _product_names(catalog: pd.DataFrame) -> dict[str, str]:
    return dict(zip(catalog["product_id"], catalog["catalog_name"], strict=True))


def deliver_digest(
    result: dict[str, pd.DataFrame], site_name: str, today: date, dry_run: bool
) -> str:
    site_id = _site_id(site_name)
    subject, text, html_body = build_digest(
        result["alert"], result["fact_contract"], result["dim_owner"], site_id, today,
        dq_issues=len(result["dq_issue"]), dashboard_url=os.environ.get("DASHBOARD_URL"),
        product_names=_product_names(result["dim_product"]),
    )
    if dry_run:
        return f"{subject}\n\n{text}"
    to = recipients(site_id, os.environ)
    send_email(subject, text, html_body, to, SmtpSettings.from_env(os.environ))
    return f"digest sent: {subject} -> {', '.join(to)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the license data quality pipeline.")
    parser.add_argument("--raw-dir", type=Path, default=config.RAW_DIR)
    parser.add_argument("--out-dir", type=Path, default=config.CURATED_DIR)
    parser.add_argument("--generate", action="store_true", help="regenerate synthetic raw data")
    parser.add_argument("--local", action="store_true", help="skip BigQuery even if configured")
    parser.add_argument("--today", type=date.fromisoformat, default=config.TODAY)
    parser.add_argument("--digest", choices=[n.lower() for n, _ in config.SITES.values()])
    parser.add_argument("--dry-run", action="store_true", help="print the digest, do not send")
    parser.add_argument("--force", action="store_true", help="send even outside 09:00 local time")
    args = parser.parse_args(argv)
    if args.digest and not args.force and not should_send(_site_id(args.digest), _utc_now()):
        print(f"skipped: it is not 09:00 local time in {args.digest.title()}")
        return 0
    result = run(
        raw_dir=args.raw_dir, out_dir=args.out_dir, today=args.today, generate_data=args.generate,
        project=os.environ.get("GCP_PROJECT"),
        dataset=os.environ.get("BQ_DATASET", DEFAULT_DATASET), local_only=args.local,
    )
    log = result["pipeline_run_log"].iloc[0]
    print(
        f"{log['run_id']} {log['status']} rows_in={log['rows_in']} "
        f"rows_out={log['rows_out']} issues={log['issues']} alerts={len(result['alert'])}"
    )
    if args.digest:
        print(deliver_digest(result, args.digest, args.today, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
