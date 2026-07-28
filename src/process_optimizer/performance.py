"""Cycle-time, bottleneck, rework, and workload analytics."""

from __future__ import annotations

import pandas as pd


def transition_waits(events: pd.DataFrame) -> pd.DataFrame:
    """Return case-level transition waits."""

    ordered = events.sort_values(["case_id", "timestamp", "event_index"]).copy()
    ordered["previous_activity"] = ordered.groupby("case_id")["activity"].shift(1)
    ordered["previous_timestamp"] = ordered.groupby("case_id")["timestamp"].shift(1)
    result = ordered.dropna(subset=["previous_activity", "previous_timestamp"]).copy()
    result["wait_hours"] = (
        result["timestamp"] - result["previous_timestamp"]
    ).dt.total_seconds() / 3600
    return result[
        [
            "case_id",
            "previous_activity",
            "activity",
            "wait_hours",
            "resource_role",
            "business_unit",
            "department",
        ]
    ].reset_index(drop=True)


def bottleneck_table(events: pd.DataFrame) -> pd.DataFrame:
    """Rank activities by waiting-time exposure and case reach."""

    waits = transition_waits(events)
    total_cases = events["case_id"].nunique()
    result = (
        waits.groupby("activity", as_index=False)
        .agg(
            case_count=("case_id", "nunique"),
            transition_count=("case_id", "size"),
            total_wait_hours=("wait_hours", "sum"),
            mean_wait_hours=("wait_hours", "mean"),
            median_wait_hours=("wait_hours", "median"),
            p90_wait_hours=("wait_hours", lambda values: values.quantile(0.90)),
            p95_wait_hours=("wait_hours", lambda values: values.quantile(0.95)),
        )
        .sort_values(["total_wait_hours", "activity"], ascending=[False, True])
    )
    result["case_coverage"] = result["case_count"] / total_cases
    result["bottleneck_score"] = (
        0.55 * result["total_wait_hours"] / result["total_wait_hours"].max()
        + 0.30 * result["p90_wait_hours"] / result["p90_wait_hours"].max()
        + 0.15 * result["case_coverage"]
    )
    return result.sort_values(
        ["bottleneck_score", "activity"], ascending=[False, True]
    ).reset_index(drop=True)


def case_performance(events: pd.DataFrame) -> pd.DataFrame:
    """Compute case-level cycle, touch, wait, rework, and automation metrics."""

    ordered = events.sort_values(["case_id", "timestamp", "event_index"])
    grouped = ordered.groupby("case_id", sort=True)
    result = grouped.agg(
        created_at=("timestamp", "min"),
        completed_at=("timestamp", "max"),
        event_count=("activity", "size"),
        unique_activity_count=("activity", "nunique"),
        processing_minutes=("processing_minutes", "sum"),
        automated_event_count=("automated", "sum"),
    ).reset_index()
    result["cycle_time_hours"] = (
        result["completed_at"] - result["created_at"]
    ).dt.total_seconds() / 3600
    result["touch_time_hours"] = result["processing_minutes"] / 60
    result["estimated_wait_hours"] = (result["cycle_time_hours"] - result["touch_time_hours"]).clip(
        lower=0
    )
    result["rework_event_count"] = (result["event_count"] - result["unique_activity_count"]).clip(
        lower=0
    )
    result["automation_rate"] = result["automated_event_count"] / result["event_count"]
    return result


def rework_summary(events: pd.DataFrame) -> pd.DataFrame:
    """Rank repeated activities by affected cases and repeat volume."""

    counts = (
        events.groupby(["case_id", "activity"], as_index=False)
        .size()
        .rename(columns={"size": "occurrences"})
    )
    repeats = counts[counts["occurrences"] > 1].copy()
    if repeats.empty:
        return pd.DataFrame(
            columns=["activity", "affected_cases", "repeat_events", "mean_occurrences"]
        )
    repeats["repeat_events"] = repeats["occurrences"] - 1
    return (
        repeats.groupby("activity", as_index=False)
        .agg(
            affected_cases=("case_id", "nunique"),
            repeat_events=("repeat_events", "sum"),
            mean_occurrences=("occurrences", "mean"),
        )
        .sort_values(["repeat_events", "activity"], ascending=[False, True])
        .reset_index(drop=True)
    )


def resource_workload(events: pd.DataFrame) -> pd.DataFrame:
    """Summarize work concentration and manual workload by resource."""

    result = (
        events.groupby(["resource_id", "resource_role"], as_index=False)
        .agg(
            event_count=("case_id", "size"),
            case_count=("case_id", "nunique"),
            processing_hours=("processing_minutes", lambda values: values.sum() / 60),
            automated_rate=("automated", "mean"),
        )
        .sort_values(["processing_hours", "resource_id"], ascending=[False, True])
    )
    total_hours = float(result["processing_hours"].sum())
    result["workload_share"] = result["processing_hours"] / total_hours if total_hours else 0.0
    return result.reset_index(drop=True)
