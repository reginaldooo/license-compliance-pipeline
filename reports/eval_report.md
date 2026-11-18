# Evaluation report

All data is synthetic. Results show how well the rules recover cases injected by the generator (seed fixed). They are not a measure of accuracy on real data.

Injected cases sit well clear of every threshold, so a perfect score here shows the rules are implemented as specified. It does not show they would hold up on borderline real-world cases.

## Record counts

| Table | Rows |
|---|---|
| owners | 25 |
| contracts | 152 |
| inventory | 136 |
| usage | 1500 |
| ai_seats | 200 |
| contracts after quarantine | 120 |
| dq_issue rows | 62 |
| alert rows | 677 |

## Alert rules: precision and recall

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 629 | 629 | 629 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |

## Data quality checks: precision and recall

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| contract_without_inventory | 9 | 9 | 9 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 13 | 13 | 13 | 0 | 0 | 100.0% | 100.0% |
| missing_owner | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 8 | 8 | 8 | 0 | 0 | 100.0% | 100.0% |

## Mismatches

- None
