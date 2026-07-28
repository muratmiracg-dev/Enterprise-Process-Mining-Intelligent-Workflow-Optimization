# SLA breach model card

## Intended use

Prioritize analyst review of Purchase-to-Pay cases after Purchase Order creation.
The score must not approve/reject a request, block a vendor, or authorize payment.

## Model

- Algorithm: class-weighted logistic regression
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
| Brier score | 0.1693 |

Confusion matrix at threshold 0.50: TN 1,200; FP 314; FN 272; TP 614.

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
- Probability calibration and data drift are not yet continuously monitored.

## Production acceptance

Require data-protection review, real temporal backtest, calibration curve,
subgroup error analysis, threshold-cost study, analyst pilot, monitoring,
versioned approval, and rollback.
