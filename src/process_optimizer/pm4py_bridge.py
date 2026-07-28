"""Small, testable PM4Py integration boundary."""

from __future__ import annotations

from typing import Any

import pandas as pd


class PM4PyUnavailable(RuntimeError):
    """Raised when the optional process-mining runtime is unavailable."""


def _pm4py() -> Any:
    try:
        import pm4py
    except ImportError as exc:  # pragma: no cover - exercised through monkeypatch
        raise PM4PyUnavailable(
            "PM4Py is required for reference-algorithm discovery; install the process extra."
        ) from exc
    return pm4py


def prepare_dataframe(events: pd.DataFrame) -> pd.DataFrame:
    """Map the canonical contract to PM4Py's event-log semantics."""

    pm4py = _pm4py()
    frame = events[["case_id", "activity", "timestamp", "resource_id"]].copy()
    return pm4py.format_dataframe(
        frame,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
    )


def discover_reference_model(
    events: pd.DataFrame,
    *,
    sample_cases: int = 2_000,
) -> dict[str, object]:
    """Discover DFG and process tree through PM4Py on a deterministic case sample."""

    pm4py = _pm4py()
    case_ids = sorted(events["case_id"].unique())[:sample_cases]
    sample = events[events["case_id"].isin(case_ids)].copy()
    formatted = prepare_dataframe(sample)
    dfg, starts, ends = pm4py.discover_dfg(formatted)
    tree = pm4py.discover_process_tree_inductive(formatted)
    return {
        "pm4py_version": str(getattr(pm4py, "__version__", "unknown")),
        "sample_cases": int(len(case_ids)),
        "dfg_edges": int(len(dfg)),
        "start_activities": {str(key): int(value) for key, value in starts.items()},
        "end_activities": {str(key): int(value) for key, value in ends.items()},
        "process_tree": str(tree),
    }
