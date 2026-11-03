# Changelog

All notable changes follow a simplified Keep a Changelog structure.

## [Unreleased]

### Fixed

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
