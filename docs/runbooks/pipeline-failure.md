# Runbook: analysis pipeline failure

1. Confirm `/readyz` and inspect the latest analysis run metric.
2. Capture the data version, code revision, command, and sanitized traceback.
3. Run contract validation before retrying the full pipeline.
4. Compare event/case identifiers and declared counts.
5. If code caused the failure, roll back to the prior immutable image.
6. Do not overwrite the failed input or evidence.
7. Re-run tests and acceptance checks before restoring service.
