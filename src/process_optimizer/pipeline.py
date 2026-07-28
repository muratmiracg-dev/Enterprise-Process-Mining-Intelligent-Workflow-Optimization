"""End-to-end process intelligence pipeline."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from process_optimizer.config import IDEAL_PROCESS
from process_optimizer.conformance import conformance_table, deviation_summary
from process_optimizer.discovery import (
    activity_summary,
    directly_follows_graph,
    variant_table,
)
from process_optimizer.performance import (
    bottleneck_table,
    case_performance,
    resource_workload,
    rework_summary,
)
from process_optimizer.pm4py_bridge import PM4PyUnavailable, discover_reference_model
from process_optimizer.prediction import PredictionResult, train_sla_model
from process_optimizer.repository import EventLogRepository
from process_optimizer.simulation import simulate_capacity
from process_optimizer.telemetry import (
    ANALYSIS_DURATION,
    ANALYSIS_RUNS,
    CASES_LOADED,
    EVENTS_LOADED,
    SLA_ADHERENCE,
)


def _round(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def _record(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    selected = frame.head(limit) if limit is not None else frame
    return json.loads(selected.to_json(orient="records", date_format="iso"))


def _write_table(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def _risk_distribution(prediction: PredictionResult) -> list[dict[str, Any]]:
    order = ["Low", "Medium", "High", "Critical"]
    counts = prediction.predictions["risk_band"].value_counts()
    total = max(int(counts.sum()), 1)
    return [
        {
            "risk_band": band,
            "case_count": int(counts.get(band, 0)),
            "case_share": _round(int(counts.get(band, 0)) / total),
        }
        for band in order
    ]


def analyze_frames(
    events: pd.DataFrame,
    cases: pd.DataFrame,
    *,
    include_pm4py: bool = True,
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    """Analyze validated in-memory frames and return report plus tables."""

    variants = variant_table(events)
    dfg = directly_follows_graph(events)
    activities = activity_summary(events)
    conformance = conformance_table(events, IDEAL_PROCESS)
    deviations = deviation_summary(conformance)
    bottlenecks = bottleneck_table(events)
    performance = case_performance(events)
    rework = rework_summary(events)
    resources = resource_workload(events)
    prediction = train_sla_model(events, cases)
    simulations = simulate_capacity()

    case_enriched = cases.merge(
        conformance[["case_id", "fitness", "conformant"]],
        on="case_id",
        how="left",
    ).merge(
        performance[
            [
                "case_id",
                "touch_time_hours",
                "estimated_wait_hours",
                "automation_rate",
            ]
        ],
        on="case_id",
        how="left",
    )

    sla_adherence = 1 - float(cases["sla_breached"].mean())
    rework_case_rate = float((cases["rework_count"] > 0).mean())
    wait_share = float(
        performance["estimated_wait_hours"].sum() / max(performance["cycle_time_hours"].sum(), 1)
    )
    best_scenario = simulations.iloc[-1]

    pm4py_reference: dict[str, object]
    if include_pm4py:
        try:
            pm4py_reference = discover_reference_model(events)
        except PM4PyUnavailable as exc:
            pm4py_reference = {"available": False, "reason": str(exc)}
    else:
        pm4py_reference = {"available": False, "reason": "disabled by caller"}

    report: dict[str, Any] = {
        "project": {
            "name": "Enterprise Process Mining & Intelligent Workflow Optimization",
            "process": "Purchase-to-Pay",
            "dataset": "Northstar Manufacturing Group synthetic portfolio data",
            "currency": "USD",
            "generated_with_seed": 20260728,
            "disclaimer": (
                "All organizations, resources, vendors, transactions, events, "
                "predictions, and business-impact estimates are synthetic."
            ),
        },
        "data_quality": {
            "event_count": int(len(events)),
            "case_count": int(cases["case_id"].nunique()),
            "activity_count": int(events["activity"].nunique()),
            "resource_count": int(events["resource_id"].nunique()),
            "variant_count": int(len(variants)),
            "start_timestamp": events["timestamp"].min().isoformat(),
            "end_timestamp": events["timestamp"].max().isoformat(),
            "event_case_reconciliation": True,
            "duplicate_case_event_keys": int(events.duplicated(["case_id", "event_index"]).sum()),
            "null_required_fields": int(
                events[["case_id", "activity", "timestamp"]].isna().sum().sum()
            ),
        },
        "kpis": {
            "median_cycle_hours": _round(cases["cycle_time_hours"].median(), 2),
            "p90_cycle_hours": _round(cases["cycle_time_hours"].quantile(0.90), 2),
            "p95_cycle_hours": _round(cases["cycle_time_hours"].quantile(0.95), 2),
            "sla_adherence": _round(sla_adherence),
            "straight_through_rate": _round(float(conformance["conformant"].mean())),
            "mean_conformance_fitness": _round(float(conformance["fitness"].mean())),
            "rework_case_rate": _round(rework_case_rate),
            "automation_event_rate": _round(float(events["automated"].mean())),
            "wait_time_share": _round(wait_share),
            "annualized_case_volume": 8_000,
        },
        "process_discovery": {
            "ideal_path": list(IDEAL_PROCESS),
            "top_variants": _record(variants, 12),
            "top_transitions": _record(dfg, 20),
            "activities": _record(activities),
            "pm4py_reference": pm4py_reference,
        },
        "conformance": {
            "conformant_cases": int(conformance["conformant"].sum()),
            "nonconformant_cases": int((~conformance["conformant"]).sum()),
            "deviations": _record(deviations, 20),
        },
        "performance": {
            "top_bottlenecks": _record(bottlenecks, 12),
            "rework": _record(rework, 12),
            "resource_workload": _record(resources, 15),
        },
        "sla_prediction": {
            "metrics": prediction.metrics,
            "risk_distribution": _risk_distribution(prediction),
            "top_drivers": _record(prediction.feature_importance, 15),
        },
        "capacity_simulation": {
            "method": (
                "Replicated queue-network simulation: 24 replications x 900 cases "
                "per scenario with fixed seed and explicit capacity assumptions."
            ),
            "scenarios": _record(simulations),
            "recommended_scenario": str(best_scenario["scenario"]),
            "recommended_cycle_reduction_pct": _round(
                float(best_scenario["cycle_time_reduction_pct"])
            ),
            "recommended_sla_uplift_pp": _round(float(best_scenario["sla_adherence_uplift_pp"]), 2),
            "estimated_annual_value_usd": _round(
                float(best_scenario["estimated_annual_value_usd"]), 2
            ),
            "first_year_roi": _round(float(best_scenario["first_year_roi"])),
        },
        "governance": {
            "decision_mode": "human-in-the-loop",
            "production_mutations": False,
            "prediction_use": (
                "Prioritize analyst review; never approve, reject, or pay an invoice "
                "without an authorized business control."
            ),
            "model_validation": "Temporal holdout; synthetic data; not production calibrated.",
        },
    }
    tables = {
        "activities": activities,
        "bottlenecks": bottlenecks,
        "case_conformance": conformance,
        "case_performance": case_enriched,
        "deviations": deviations,
        "directly_follows_graph": dfg,
        "resource_workload": resources,
        "rework": rework,
        "risk_predictions": prediction.predictions,
        "sla_model_drivers": prediction.feature_importance,
        "simulation_scenarios": simulations,
        "variants": variants,
    }
    return report, tables


def analyze_event_log(
    event_log_path: str | Path,
    case_path: str | Path,
    *,
    output_path: str | Path | None = None,
    tables_dir: str | Path | None = None,
    include_pm4py: bool = True,
) -> dict[str, Any]:
    """Load, validate, analyze, and optionally persist process outputs."""

    started = time.perf_counter()
    try:
        events, cases = EventLogRepository(Path(event_log_path), Path(case_path)).load()
        report, tables = analyze_frames(events, cases, include_pm4py=include_pm4py)

        if output_path is not None:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        if tables_dir is not None:
            directory = Path(tables_dir)
            for name, frame in tables.items():
                _write_table(frame, directory / f"{name}.csv")

        EVENTS_LOADED.set(len(events))
        CASES_LOADED.set(cases["case_id"].nunique())
        SLA_ADHERENCE.set(1 - cases["sla_breached"].mean())
        ANALYSIS_RUNS.labels(status="success").inc()
        return report
    except Exception:
        ANALYSIS_RUNS.labels(status="failure").inc()
        raise
    finally:
        ANALYSIS_DURATION.observe(time.perf_counter() - started)
