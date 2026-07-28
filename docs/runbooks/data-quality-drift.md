# Runbook: data-quality drift

1. Quarantine the new input; keep the last known-good output active.
2. Check volume, required-field nulls, duplicate keys, timestamps, and case counts.
3. Compare activity and source-system distributions with the prior version.
4. Determine whether the drift is a legitimate process change or ingestion defect.
5. Update contracts only after owner approval and backward-impact analysis.
6. Reconcile, regenerate decision outputs, and document the change.
