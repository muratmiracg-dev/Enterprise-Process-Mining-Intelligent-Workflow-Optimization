# Dashboard build specification

## Page 1 — Executive command center

- KPI cards: Cases, Events, Median Cycle Hours, SLA Adherence, Straight-Through
  Rate, Conformance Fitness.
- Scenario selector with recommended action banner.
- Cycle time and SLA comparison by scenario.
- Business unit, country, vendor tier, and priority slicers.

## Page 2 — Process discovery

- Sankey/custom process map based on `directly_follows_graph.csv`.
- Top variants and cumulative case coverage.
- Activity volume, case coverage, and automation rate.

## Page 3 — Conformance

- Fitness distribution and conformant/nonconformant split.
- Missing, unexpected, and repeated activity table.
- Drill-through to case-level deviation evidence.

## Page 4 — Bottlenecks and rework

- Bottleneck score ranking.
- Total and p90 wait by activity.
- Rework volume and affected cases.
- Resource workload concentration.

## Page 5 — SLA risk

- Risk-band distribution.
- Case review queue with risk score and amount.
- Model performance cards: ROC AUC, average precision, recall, and Brier score.
- Explainability view using coefficient magnitude and direction.

## Page 6 — Capacity what-if

- Baseline, approval automation, AP capacity, and combined scenarios.
- Cycle time, SLA, throughput, annual value, investment, and first-year ROI.
- Assumption tooltip sourced from `docs/simulation-methodology.md`.

## Page 7 — Data quality and governance

- Event/case reconciliation, required-field nulls, duplicate keys, data window.
- Human-in-the-loop decision policy and model limitations.

## Page 8 — Case explorer

- Searchable case list with variant, cycle time, SLA, conformance, and risk.
- Drill-through event timeline.

All percentages must use measure-driven calculations. The static benchmark for
acceptance is `reports/demo-analysis.json`.
