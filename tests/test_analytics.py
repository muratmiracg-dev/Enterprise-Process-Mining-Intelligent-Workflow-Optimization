from __future__ import annotations

import pandas as pd
import pytest

from process_optimizer.conformance import (
    conformance_table,
    deviation_summary,
    levenshtein_distance,
    sequence_fitness,
)
from process_optimizer.discovery import (
    activity_summary,
    case_sequences,
    directly_follows_graph,
    variant_table,
)
from process_optimizer.performance import (
    bottleneck_table,
    case_performance,
    resource_workload,
    rework_summary,
    transition_waits,
)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ((), (), 0),
        (("a",), (), 1),
        (("a",), ("a",), 0),
        (("a", "b"), ("a", "c"), 1),
        (("a",), ("a", "b"), 1),
    ],
)
def test_levenshtein_distance(left, right, expected: int) -> None:
    assert levenshtein_distance(left, right) == expected


def test_sequence_fitness_is_normalized() -> None:
    assert sequence_fitness(("a", "b"), ("a", "b")) == 1
    assert sequence_fitness((), ()) == 1
    assert sequence_fitness(("x", "y"), ("a", "b")) == 0


def test_case_sequences_and_variants(ideal_events: pd.DataFrame) -> None:
    sequences = case_sequences(ideal_events)
    variants = variant_table(ideal_events)
    assert sequences.loc["C-1"] == ("Start", "Review", "Close")
    assert variants["case_count"].sum() == 2
    assert variants["case_share"].sum() == pytest.approx(1)
    assert variants["variant_rank"].tolist() == [1, 2]


def test_dfg_has_frequency_and_wait(ideal_events: pd.DataFrame) -> None:
    graph = directly_follows_graph(ideal_events)
    review_close = graph.query("source == 'Review' and target == 'Close'").iloc[0]
    assert review_close["transition_count"] == 2
    assert review_close["mean_wait_hours"] == pytest.approx(1.5)


def test_activity_summary(ideal_events: pd.DataFrame) -> None:
    summary = activity_summary(ideal_events).set_index("activity")
    assert summary.loc["Review", "event_count"] == 3
    assert summary.loc["Close", "automation_rate"] == 1
    assert summary.loc["Start", "case_coverage"] == 1


def test_conformance_explains_repetition(ideal_events: pd.DataFrame) -> None:
    result = conformance_table(ideal_events, ("Start", "Review", "Close"))
    assert result.loc[result["case_id"] == "C-1", "conformant"].iloc[0]
    second = result.loc[result["case_id"] == "C-2"].iloc[0]
    assert second["fitness"] == pytest.approx(0.75)
    assert second["repeated_activities"] == "Review"
    deviations = deviation_summary(result)
    assert deviations.to_dict("records") == [
        {"deviation_type": "repeated", "activity": "Review", "case_count": 1}
    ]


def test_deviation_summary_handles_empty() -> None:
    frame = pd.DataFrame(
        [
            {
                "missing_activities": "",
                "unexpected_activities": "",
                "repeated_activities": "",
            }
        ]
    )
    result = deviation_summary(frame)
    assert list(result.columns) == ["deviation_type", "activity", "case_count"]
    assert result.empty


def test_transition_and_bottleneck_metrics(ideal_events: pd.DataFrame) -> None:
    waits = transition_waits(ideal_events)
    assert len(waits) == 5
    bottlenecks = bottleneck_table(ideal_events)
    assert bottlenecks.iloc[0]["bottleneck_score"] <= 1
    assert bottlenecks["case_coverage"].between(0, 1).all()


def test_case_performance(ideal_events: pd.DataFrame) -> None:
    result = case_performance(ideal_events).set_index("case_id")
    assert result.loc["C-1", "cycle_time_hours"] == 3
    assert result.loc["C-2", "rework_event_count"] == 1
    assert result.loc["C-1", "automation_rate"] == pytest.approx(1 / 3)
    assert result.loc["C-1", "estimated_wait_hours"] > 0


def test_rework_summary(ideal_events: pd.DataFrame) -> None:
    result = rework_summary(ideal_events)
    assert result.iloc[0]["activity"] == "Review"
    assert result.iloc[0]["repeat_events"] == 1
    empty = rework_summary(ideal_events.drop_duplicates(["case_id", "activity"]))
    assert empty.empty


def test_resource_workload(ideal_events: pd.DataFrame) -> None:
    result = resource_workload(ideal_events)
    assert result["workload_share"].sum() == pytest.approx(1)
    assert result.iloc[0]["resource_id"] == "R-2"


def test_resource_workload_zero_hours(ideal_events: pd.DataFrame) -> None:
    result = resource_workload(ideal_events.assign(processing_minutes=0))
    assert result["workload_share"].eq(0).all()
