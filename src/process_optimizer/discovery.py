"""Process discovery primitives with deterministic outputs."""

from __future__ import annotations

from collections import Counter

import pandas as pd


def case_sequences(events: pd.DataFrame) -> pd.Series:
    """Return the ordered activity tuple for every case."""

    return events.groupby("case_id", sort=True)["activity"].agg(tuple)


def variant_table(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate process variants by frequency and share."""

    sequences = case_sequences(events)
    counts = Counter(sequences)
    rows = [
        {
            "variant": " > ".join(sequence),
            "activity_count": len(sequence),
            "case_count": count,
        }
        for sequence, count in counts.items()
    ]
    result = pd.DataFrame(rows).sort_values(["case_count", "variant"], ascending=[False, True])
    result["case_share"] = result["case_count"] / int(result["case_count"].sum())
    result.insert(0, "variant_rank", range(1, len(result) + 1))
    return result.reset_index(drop=True)


def directly_follows_graph(events: pd.DataFrame) -> pd.DataFrame:
    """Build a directly-follows graph with frequency and transition duration."""

    ordered = events.sort_values(["case_id", "timestamp", "event_index"]).copy()
    ordered["next_activity"] = ordered.groupby("case_id")["activity"].shift(-1)
    ordered["next_timestamp"] = ordered.groupby("case_id")["timestamp"].shift(-1)
    transitions = ordered.dropna(subset=["next_activity", "next_timestamp"]).copy()
    transitions["wait_hours"] = (
        transitions["next_timestamp"] - transitions["timestamp"]
    ).dt.total_seconds() / 3600

    result = (
        transitions.groupby(["activity", "next_activity"], as_index=False)
        .agg(
            transition_count=("case_id", "size"),
            mean_wait_hours=("wait_hours", "mean"),
            median_wait_hours=("wait_hours", "median"),
            p90_wait_hours=("wait_hours", lambda values: values.quantile(0.90)),
        )
        .rename(columns={"activity": "source", "next_activity": "target"})
    )
    total_cases = events["case_id"].nunique()
    result["case_coverage"] = result["transition_count"] / total_cases
    return result.sort_values(
        ["transition_count", "source", "target"], ascending=[False, True, True]
    ).reset_index(drop=True)


def activity_summary(events: pd.DataFrame) -> pd.DataFrame:
    """Summarize activity frequency, automation, processing, and case reach."""

    total_cases = events["case_id"].nunique()
    result = (
        events.groupby("activity", as_index=False)
        .agg(
            event_count=("case_id", "size"),
            case_count=("case_id", "nunique"),
            automation_rate=("automated", "mean"),
            mean_processing_minutes=("processing_minutes", "mean"),
            median_processing_minutes=("processing_minutes", "median"),
        )
        .sort_values(["event_count", "activity"], ascending=[False, True])
    )
    result["case_coverage"] = result["case_count"] / total_cases
    return result.reset_index(drop=True)
