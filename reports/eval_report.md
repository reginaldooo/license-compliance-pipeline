# Evaluation report

All data is synthetic. Results show how well the rules recover cases injected by the generator, summed over 5 seeds per scenario. They are not a measure of accuracy on real data.

Labels come from the generator and follow the rule definitions in the README, written separately from the rule code. Scenarios other than `baseline` add borderline cases, messier data, conflicts, or more volume, and are where mismatches show up.

## Summary

| Scenario | Alert precision | Alert recall | DQ precision | DQ recall | Name match precision | Name match recall |
|---|---|---|---|---|---|---|
| baseline | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| borderline | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| combined | 100.0% | 100.0% | 99.7% | 99.9% | 100.0% | 99.7% |
| conflict | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| messy | 100.0% | 100.0% | 99.4% | 100.0% | 100.0% | 99.5% |
| scale | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

## Scenario: baseline

Clean spreadsheets. Injected cases sit well clear of thresholds.

| Table (first seed) | Rows |
|---|---|
| owners | 25 |
| contracts | 152 |
| inventory | 130 |
| usage | 1500 |
| ai_seats | 200 |
| contracts after quarantine | 120 |
| dq_issue rows | 69 |
| alert rows | 677 |

### Alert rules

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 3145 | 3145 | 3145 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |

### Data quality checks

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| contract_without_inventory | 83 | 83 | 83 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 75 | 75 | 75 | 0 | 0 | 100.0% | 100.0% |
| missing_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |

### Product name matching

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| name_match | 622 | 622 | 622 | 0 | 0 | 100.0% | 100.0% |

### Mismatches

- None

## Scenario: borderline

Near-miss cases on both sides of every threshold: renewals at 30/31/60/61/90/91 days, installs at entitlement -1/0/+1, seats idle 89 to 92 days, moderate install growth.

| Table (first seed) | Rows |
|---|---|
| owners | 25 |
| contracts | 152 |
| inventory | 131 |
| usage | 1500 |
| ai_seats | 200 |
| contracts after quarantine | 120 |
| dq_issue rows | 74 |
| alert rows | 703 |

### Alert rules

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 50 | 50 | 50 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 50 | 50 | 50 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 3173 | 3173 | 3173 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 55 | 55 | 55 | 0 | 0 | 100.0% | 100.0% |

### Data quality checks

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| contract_without_inventory | 83 | 83 | 83 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 84 | 84 | 84 | 0 | 0 | 100.0% | 100.0% |
| missing_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |

### Product name matching

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| name_match | 623 | 623 | 623 | 0 | 0 | 100.0% | 100.0% |

### Mismatches

- None

## Scenario: combined

Everything at once: borderline cases, messy data, conflicts, and about twice the volume.

| Table (first seed) | Rows |
|---|---|
| owners | 25 |
| contracts | 312 |
| inventory | 148 |
| usage | 3000 |
| ai_seats | 400 |
| contracts after quarantine | 240 |
| dq_issue rows | 133 |
| alert rows | 1333 |

### Alert rules

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 50 | 50 | 50 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 50 | 50 | 50 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 6315 | 6315 | 6315 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 55 | 55 | 55 | 0 | 0 | 100.0% | 100.0% |

### Data quality checks

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| conflicting_duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| contract_without_inventory | 164 | 164 | 164 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| expired_contract | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 74 | 73 | 73 | 0 | 1 | 100.0% | 98.6% |
| missing_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| missing_value | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unknown_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 120 | 122 | 120 | 2 | 0 | 98.4% | 100.0% |

### Product name matching

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| name_match | 625 | 623 | 623 | 0 | 2 | 100.0% | 99.7% |

### Mismatches

- `inventory_without_contract` missed (1): I00122
- `unmapped_product` false positives (2): I00060, I00122
- `name_match` missed (2): I00060->P009, I00122->P009

## Scenario: conflict

Contract ids that appear twice with different values, contracts that already expired, and contracts whose owner does not exist.

| Table (first seed) | Rows |
|---|---|
| owners | 25 |
| contracts | 184 |
| inventory | 126 |
| usage | 1500 |
| ai_seats | 200 |
| contracts after quarantine | 120 |
| dq_issue rows | 96 |
| alert rows | 677 |

### Alert rules

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 3145 | 3145 | 3145 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |

### Data quality checks

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| conflicting_duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| contract_without_inventory | 83 | 83 | 83 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| expired_contract | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 76 | 76 | 76 | 0 | 0 | 100.0% | 100.0% |
| missing_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unknown_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |

### Product name matching

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| name_match | 628 | 628 | 628 | 0 | 0 | 100.0% | 100.0% |

### Mismatches

- None

## Scenario: messy

Harsher product-name noise, extra date formats, blank contract fields, and three times as many unknown products.

| Table (first seed) | Rows |
|---|---|
| owners | 25 |
| contracts | 160 |
| inventory | 144 |
| usage | 1500 |
| ai_seats | 200 |
| contracts after quarantine | 120 |
| dq_issue rows | 97 |
| alert rows | 677 |

### Alert rules

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 3145 | 3145 | 3145 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |

### Data quality checks

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| contract_without_inventory | 83 | 83 | 83 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 78 | 78 | 78 | 0 | 0 | 100.0% | 100.0% |
| missing_owner | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| missing_value | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 40 | 40 | 40 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 120 | 123 | 120 | 3 | 0 | 97.6% | 100.0% |

### Product name matching

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| name_match | 615 | 612 | 612 | 0 | 3 | 100.0% | 99.5% |

### Mismatches

- `unmapped_product` false positives (3): I00012, I00064, I00073
- `name_match` missed (3): I00012->P009, I00064->P009, I00073->P009

## Scenario: scale

Eight times the volume with the same noise level.

| Table (first seed) | Rows |
|---|---|
| owners | 25 |
| contracts | 1008 |
| inventory | 135 |
| usage | 12000 |
| ai_seats | 1600 |
| contracts after quarantine | 960 |
| dq_issue rows | 186 |
| alert rows | 5104 |

### Alert rules

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| installs_over_entitlement | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| price_change_renewal | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_30 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_60 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| renewal_90 | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| seat_unused_90d | 25160 | 25160 | 25160 | 0 | 0 | 100.0% | 100.0% |
| usage_spike | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |

### Data quality checks

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| contract_without_inventory | 616 | 616 | 616 | 0 | 0 | 100.0% | 100.0% |
| duplicate | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| invalid_date | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| inventory_without_contract | 79 | 79 | 79 | 0 | 0 | 100.0% | 100.0% |
| missing_owner | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| negative_seats | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |
| unmapped_product | 60 | 60 | 60 | 0 | 0 | 100.0% | 100.0% |

### Product name matching

| Rule | Injected | Flagged | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|---|---|
| name_match | 640 | 640 | 640 | 0 | 0 | 100.0% | 100.0% |

### Mismatches

- None
