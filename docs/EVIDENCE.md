# Evidence

This file lets a reviewer check that the pipeline runs on its own, without taking my word for it. Everything here uses synthetic data.

## What each claim rests on

| Claim | Evidence | How to check it |
|---|---|---|
| Tests and lint pass | The CI badge in the README and the [CI workflow runs](https://github.com/reginaldooo/license-compliance-pipeline/actions/workflows/ci.yml) | Run `uv run pytest` and `uv run ruff check .` |
| Each rule's precision and recall is measured | [`reports/eval_report.md`](https://github.com/reginaldooo/license-compliance-pipeline/blob/main/reports/eval_report.md), rebuilt on every CI run | Run `uv run python -m license_pipeline.evaluate` |
| It runs unattended on a schedule | The table below, built from the [Daily digest workflow runs](https://github.com/reginaldooo/license-compliance-pipeline/actions/workflows/daily-digest.yml) | Open any run link. Rows marked `scheduled` started by cron, `manual` ones were started by hand |
| Results land in BigQuery | The `pipeline_run_log` table has one row per run with row counts, issue count, and status | Query it in the BigQuery console |
| The digest email arrives | Screenshots in [`docs/evidence/`](https://github.com/reginaldooo/license-compliance-pipeline/tree/main/docs/evidence), added by hand with personal addresses cropped | Open the image files |

## Recent runs (last 7 days)

This table is rewritten by a workflow after each digest run. Runs older than 7 days are dropped on purpose.

<!-- runs:start -->
2 runs in the last 7 days: 0 scheduled, 2 manual; 1 succeeded, 1 failed.

| Run time (UTC) | Trigger | Result | Link |
|---|---|---|---|
| 2026-11-18 09:40 | manual | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44278179929) |
| 2026-11-18 09:37 | manual | failure | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44277672354) |
<!-- runs:end -->

## Limits of this evidence

| Limit | Why it matters |
|---|---|
| Only the last 7 days are kept | GitHub deletes old run logs automatically. The table is trimmed to match, so the history is not a long-term record |
| Only `scheduled` rows show unattended operation | `manual` rows were started by hand to test or demo |
| The data is synthetic | No real users, contracts, or savings exist. Nothing here shows adoption |
| Precision and recall come from injected cases | Injected cases sit well clear of every threshold, so 100% shows the rules match their definitions, not that they would hold on real data |
| BigQuery runs on the free sandbox | Tables expire after 60 days and are refreshed by each daily run |
| This is not production monitoring | There is no on-call, alert routing, or retry beyond the GitHub failure email |
