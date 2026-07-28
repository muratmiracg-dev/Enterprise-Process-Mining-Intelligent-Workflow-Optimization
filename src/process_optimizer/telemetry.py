"""Prometheus metrics for API and pipeline observability."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

ANALYSIS_RUNS = Counter(
    "process_optimizer_analysis_runs_total",
    "Completed analytical pipeline runs.",
    ["status"],
)
ANALYSIS_DURATION = Histogram(
    "process_optimizer_analysis_duration_seconds",
    "Wall-clock duration of analytical pipeline runs.",
)
EVENTS_LOADED = Gauge(
    "process_optimizer_events_loaded",
    "Number of events in the latest validated dataset.",
)
CASES_LOADED = Gauge(
    "process_optimizer_cases_loaded",
    "Number of cases in the latest validated dataset.",
)
SLA_ADHERENCE = Gauge(
    "process_optimizer_sla_adherence_ratio",
    "SLA adherence ratio in the latest dataset.",
)
