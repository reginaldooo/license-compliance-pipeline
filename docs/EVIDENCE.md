# Evidence

This file lets a reviewer check that the pipeline runs on its own, without taking my word for it. Everything here uses synthetic data.

## What each claim rests on

| Claim | Evidence | How to check it |
|---|---|---|
| Tests and lint pass | The CI badge in the README and the [CI workflow runs](https://github.com/reginaldooo/license-compliance-pipeline/actions/workflows/ci.yml) | Run `uv run pytest` and `uv run ruff check .` |
| Each rule's precision and recall is measured on six data scenarios | [`reports/eval_report.md`](https://github.com/reginaldooo/license-compliance-pipeline/blob/main/reports/eval_report.md), rebuilt on every CI run | Run `uv run python -m license_pipeline.evaluate` |
| Each scheduled run uses a different scenario and records its own quality score | `scenario`, `alert_precision`, `alert_recall`, `dq_*` and `match_*` columns in `pipeline_run_log`, and a table on each Actions run page | Open a run, then its Summary tab |
| It runs unattended on a schedule | The table below, built from the [Daily digest workflow runs](https://github.com/reginaldooo/license-compliance-pipeline/actions/workflows/daily-digest.yml) | Open any run link. Rows marked `scheduled` started by cron, `manual` ones were started by hand |
| Results land in BigQuery | The `pipeline_run_log` table has one row per run with row counts, issue count, and status | Query it in the BigQuery console |
| The digest email arrives | Screenshots in [`docs/evidence/`](https://github.com/reginaldooo/license-compliance-pipeline/tree/main/docs/evidence), added by hand with personal addresses cropped | Open the image files |

## Recent runs (last 7 days)

This table is rewritten by a workflow after each digest run. Runs older than 7 days are dropped on purpose.

<!-- runs:start -->
14 runs in the last 7 days: 14 scheduled, 0 manual; 14 succeeded, 0 failed.

| Run time (UTC) | Trigger | Result | Link |
|---|---|---|---|
| 2026-11-25 17:43 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45667818897) |
| 2026-11-25 10:57 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45599878806) |
| 2026-11-24 19:27 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45470405423) |
| 2026-11-24 18:32 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45460584028) |
| 2026-11-24 12:06 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45390393536) |
| 2026-11-23 20:02 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45255102976) |
| 2026-11-23 18:54 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45243226280) |
| 2026-11-23 10:26 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/45156111587) |
| 2026-11-20 16:53 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44777892973) |
| 2026-11-20 15:52 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44767599038) |
| 2026-11-20 09:46 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44713588951) |
| 2026-11-19 17:14 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44575053915) |
| 2026-11-19 16:13 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44563626958) |
| 2026-11-19 09:58 | scheduled | success | [run](https://github.com/reginaldooo/license-compliance-pipeline/actions/runs/44501326532) |
<!-- runs:end -->

## Limits of this evidence

| Limit | Why it matters |
|---|---|
| Only the last 7 days are kept | GitHub deletes old run logs automatically. The table is trimmed to match, so the history is not a long-term record |
| Only `scheduled` rows show unattended operation | `manual` rows were started by hand to test or demo |
| The data is synthetic | No real users, contracts, or savings exist. Nothing here shows adoption |
| Precision and recall come from injected cases | Labels follow the written rule definitions, so 100% shows the rules match their definitions, including boundary cases. It does not show they would hold on real data. Mismatches that do appear are in product-name matching |
| BigQuery runs on the free sandbox | Tables expire after 60 days and are refreshed by each daily run |
| This is not production monitoring | There is no on-call, alert routing, or retry beyond the GitHub failure email |
