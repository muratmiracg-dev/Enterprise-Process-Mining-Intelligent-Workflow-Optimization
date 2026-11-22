# SLA breach model card

## Intended use

Prioritize analyst review of Purchase-to-Pay cases after Purchase Order creation.
The score must not approve/reject a request, block a vendor, or authorize payment. Cases without a recorded Purchase Order Created event are rejected; full cycle time is never substituted for an unavailable post-PO feature.

## Model

- Algorithm: class-weighted logistic regression; scores prior-corrected to the training
  breach rate (38.17%) so they read as breach probabilities
- Feature cut: Purchase Order creation
- Validation: chronological 80/20 holdout
- Training cases: 9,600
- Holdout cases: 2,400
- Holdout breach rate: 36.92%

## Performance

| Metric | Holdout |
|---|---:|
| ROC AUC | 0.8220 |
| Average precision | 0.7547 |
| Accuracy | 0.7558 |
| Precision | 0.6616 |
| Recall | 0.6930 |
| F1 | 0.6770 |
| Brier score | 0.1613 |
| Mean predicted risk / observed breach rate | 36.99% / 36.92% |

Confusion matrix at the review cut-off (balanced score 0.50, i.e. calibrated risk
>= 38.17%): TN 1,200; FP 314; FN 272; TP 614.

## Calibration

Class weighting makes the model fit as if breaches and non-breaches were equally common, so
its raw scores overstate risk: they averaged 0.451 against a 0.369 holdout breach rate, and the
0.60-0.80 ("High") band breached 56% of the time. The published `risk_score` adds back the
training log-odds `log(pi / (1 - pi))` (prior correction). Ranking, ROC AUC, average
precision and the review decisions are unchanged; per-band calibration on the holdout:

| Risk band | Cases | Mean risk | Observed breach rate |
|---|---:|---:|---:|
| Low (< 0.30) | 1,280 | 15.9% | 15.6% |
| Medium (0.30-0.60) | 540 | 44.8% | 43.5% |
| High (0.60-0.80) | 386 | 69.7% | 70.5% |
| Critical (>= 0.80) | 194 | 89.1% | 92.3% |

## Inputs

Numeric: amount, elapsed time to PO, early event count, approval count, early
rework count, early manual minutes.

Categorical: business unit, department, country, vendor tier, material category,
priority, and intake channel.

## Explainability

The model publishes signed coefficients and absolute magnitude. Coefficients
indicate association in the fitted feature space, not causal effect.

## Limitations and risks

- Synthetic behavior may not represent any real organization.
- Logistic regression can miss nonlinear interactions.
- Risk-band thresholds are operational conventions, not optimized policies.
- Country and organizational dimensions may proxy for process differences and
  require fairness review before real use.
- Calibration is checked on one holdout; it and data drift are not yet monitored over time.

## Production acceptance

Require data-protection review, real temporal backtest, calibration curve,
subgroup error analysis, threshold-cost study, analyst pilot, monitoring,
versioned approval, and rollback.
