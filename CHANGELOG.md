# Changelog

All notable changes follow a simplified Keep a Changelog structure.

## [Unreleased]

### Fixed

- SLA risk scores came straight from a class-weighted logistic regression, which fits as if
  breaches were as common as non-breaches. They averaged 0.451 against a 0.369 holdout breach
  rate, and cases in the "High" band (0.60-0.80) breached only 56% of the time, yet the bands
  and the Brier score treat the scores as probabilities. `risk_score` is now prior-corrected
  to the training breach rate: mean 0.370, every band within 4 points of its observed rate,
  Brier 0.1693 -> 0.1613. Ranking, ROC AUC, average precision and the review decisions
  (confusion matrix) are unchanged; the band mix moves from 880/708/446/366 to
  1,280/540/386/194 (Low/Medium/High/Critical). New metrics: `positive_rate_train`,
  `mean_predicted_risk_holdout`, `decision_threshold_risk`.
- The CI reproducibility check compared compressed `.gz` bytes, so it depended on the zlib build:
  zlib-ng (used by some Linux distributions and Python builds) produces different deflate bytes for
  identical data. `scripts/compare_demo_data.py` now compares gzip files on their decompressed
  content and header metadata (mtime 0, no embedded file name).
- CI now checks all five generated demo files. `p2p_event_log_sample.csv`, `resources.csv` and
  `ideal_process.json` were previously not compared.

## [1.0.0] — 2026-07-28

### Added

- Deterministic 12,000-case Purchase-to-Pay event generator.
- Process discovery, variants, DFG, conformance, bottlenecks, rework, and workload.
- Explainable temporal-holdout SLA risk model.
- Replicated capacity and automation simulation.
- FastAPI, PostgreSQL, Docker Compose, Prometheus, and Grafana assets.
- BPMN 2.0.2 target model and Power BI developer project.
- 58-test suite with 96.97% coverage.
- Bilingual executive report, presentation, and decision workbook.
