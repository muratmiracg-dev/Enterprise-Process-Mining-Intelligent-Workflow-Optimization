# Runbook: SLA model degradation

1. Stop automated prioritization if discrimination or calibration crosses the
   approved threshold.
2. Compare recent ROC AUC, average precision, recall, Brier score, and subgroup
   errors with the approved baseline.
3. Inspect feature and outcome drift; verify feature-cut timing.
4. Route all cases through normal human review while investigating.
5. Retrain only with versioned, approved data and repeat temporal validation.
6. Update the model card, obtain approval, and deploy with rollback ready.
