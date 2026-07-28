"""Explainable sequence conformance against the designed process."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

import pandas as pd

from process_optimizer.discovery import case_sequences


def levenshtein_distance(left: Sequence[str], right: Sequence[str]) -> int:
    """Return edit distance for two activity sequences."""

    if len(left) < len(right):
        return levenshtein_distance(right, left)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for left_index, left_value in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_value in enumerate(right, start=1):
            insert = current[right_index - 1] + 1
            delete = previous[right_index] + 1
            replace = previous[right_index - 1] + (left_value != right_value)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def sequence_fitness(observed: Sequence[str], ideal: Sequence[str]) -> float:
    """Normalize edit distance to a 0-1 conformance fitness score."""

    denominator = max(len(observed), len(ideal), 1)
    return max(0.0, 1.0 - levenshtein_distance(observed, ideal) / denominator)


def conformance_table(events: pd.DataFrame, ideal: Sequence[str]) -> pd.DataFrame:
    """Score every case and explain missing, unexpected, and repeated steps."""

    ideal_counts = Counter(ideal)
    rows: list[dict[str, object]] = []
    for case_id, sequence in case_sequences(events).items():
        observed_counts = Counter(sequence)
        missing = [
            activity
            for activity, count in ideal_counts.items()
            if observed_counts.get(activity, 0) < count
        ]
        unexpected = sorted(set(sequence) - set(ideal))
        repeated = sorted(
            activity
            for activity, count in observed_counts.items()
            if count > max(1, ideal_counts.get(activity, 0))
        )
        distance = levenshtein_distance(sequence, ideal)
        fitness = sequence_fitness(sequence, ideal)
        rows.append(
            {
                "case_id": case_id,
                "fitness": fitness,
                "edit_distance": distance,
                "conformant": distance == 0,
                "missing_activities": " | ".join(missing),
                "unexpected_activities": " | ".join(unexpected),
                "repeated_activities": " | ".join(repeated),
            }
        )
    return pd.DataFrame(rows).sort_values("case_id").reset_index(drop=True)


def deviation_summary(conformance: pd.DataFrame) -> pd.DataFrame:
    """Aggregate human-readable deviation types."""

    counter: Counter[tuple[str, str]] = Counter()
    for row in conformance.itertuples(index=False):
        for kind, value in (
            ("missing", row.missing_activities),
            ("unexpected", row.unexpected_activities),
            ("repeated", row.repeated_activities),
        ):
            for activity in filter(None, str(value).split(" | ")):
                counter[(kind, activity)] += 1
    rows = [
        {"deviation_type": kind, "activity": activity, "case_count": count}
        for (kind, activity), count in counter.items()
    ]
    if not rows:
        return pd.DataFrame(columns=["deviation_type", "activity", "case_count"])
    return (
        pd.DataFrame(rows)
        .sort_values(["case_count", "deviation_type", "activity"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
