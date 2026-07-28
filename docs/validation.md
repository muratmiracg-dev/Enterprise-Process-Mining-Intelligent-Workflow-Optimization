# Validation evidence

## Local acceptance environment

- Date: 2026-07-28
- Python: 3.12.13
- PM4Py: 2.7.22
- Dataset seed: 20260728

## Automated results

| Gate | Result |
|---|---:|
| Tests | 58 passed |
| Coverage | 96.97% |
| Cases | 12,000 |
| Events | 166,551 |
| Duplicate case/event keys | 0 |
| Null required event fields | 0 |
| Event/case reconciliation | Passed |
| PM4Py reference discovery | Passed |
| Ruff format and lint | Passed |

## Analytical reconciliation

- SLA adherence: 62.08%
- Median cycle time: 205.57 hours
- Conformance fitness: 91.62%
- Temporal holdout ROC AUC: 0.8220
- Recommended scenario: Combined Optimization
- Simulated cycle reduction: 19.42%
- Simulated SLA uplift: 13.63 percentage points

## Artifact checks

The acceptance script validates BPMN XML, JSON, CSV schemas, PBIP references,
PowerPoint slide count and source notes, PDF page count, workbook sheets, image
dimensions, required governance files, and absence of obvious secret patterns.

Power BI Desktop rendering and Docker execution are not claimed because those
runtimes are unavailable in the Linux validation environment. Their sources are
structurally checked and documented for downstream validation.
