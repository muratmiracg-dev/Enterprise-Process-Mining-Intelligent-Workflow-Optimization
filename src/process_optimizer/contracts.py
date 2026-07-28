"""Data contract validation for event logs and case-level records."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

EVENT_COLUMNS = (
    "case_id",
    "event_index",
    "activity",
    "timestamp",
    "resource_id",
    "resource_role",
    "business_unit",
    "department",
    "country",
    "vendor_id",
    "vendor_tier",
    "material_category",
    "amount_usd",
    "priority",
    "channel",
    "automated",
    "processing_minutes",
    "source_system",
)

CASE_COLUMNS = (
    "case_id",
    "created_at",
    "completed_at",
    "business_unit",
    "department",
    "country",
    "vendor_id",
    "vendor_tier",
    "material_category",
    "amount_usd",
    "priority",
    "channel",
    "variant_ground_truth",
    "event_count",
    "rework_count",
    "cycle_time_hours",
    "sla_target_hours",
    "sla_breached",
)


class ContractError(ValueError):
    """Raised when an analytical input violates its declared contract."""


def _missing(columns: Iterable[str], required: tuple[str, ...]) -> list[str]:
    present = set(columns)
    return sorted(column for column in required if column not in present)


def validate_event_log(events: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize an event log."""

    missing = _missing(events.columns, EVENT_COLUMNS)
    if missing:
        raise ContractError(f"event log is missing required columns: {missing}")
    if events.empty:
        raise ContractError("event log must contain at least one event")
    if events["case_id"].isna().any() or events["activity"].isna().any():
        raise ContractError("case_id and activity cannot contain null values")

    frame = events.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    if frame["timestamp"].isna().any():
        raise ContractError("timestamp contains invalid values")
    frame["event_index"] = pd.to_numeric(frame["event_index"], errors="coerce")
    if frame["event_index"].isna().any():
        raise ContractError("event_index contains invalid values")
    if frame.duplicated(["case_id", "event_index"]).any():
        raise ContractError("case_id and event_index must be unique")

    frame["amount_usd"] = pd.to_numeric(frame["amount_usd"], errors="coerce")
    frame["processing_minutes"] = pd.to_numeric(frame["processing_minutes"], errors="coerce")
    if frame[["amount_usd", "processing_minutes"]].isna().any().any():
        raise ContractError("numeric event fields contain invalid values")
    if (frame["amount_usd"] < 0).any() or (frame["processing_minutes"] < 0).any():
        raise ContractError("numeric event fields cannot be negative")

    if frame["automated"].dtype == object:
        normalized = frame["automated"].astype(str).str.lower()
        if not normalized.isin({"true", "false", "1", "0"}).all():
            raise ContractError("automated contains invalid boolean values")
        frame["automated"] = normalized.isin({"true", "1"})
    else:
        frame["automated"] = frame["automated"].astype(bool)
    frame = frame.sort_values(["case_id", "timestamp", "event_index"]).reset_index(drop=True)

    order_check = frame.groupby("case_id", sort=False)["timestamp"].apply(
        lambda values: values.is_monotonic_increasing
    )
    if not bool(order_check.all()):
        raise ContractError("timestamps must be monotonic within each case")
    return frame


def validate_cases(cases: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize case-level outcomes."""

    missing = _missing(cases.columns, CASE_COLUMNS)
    if missing:
        raise ContractError(f"case table is missing required columns: {missing}")
    if cases.empty:
        raise ContractError("case table must contain at least one case")
    if cases["case_id"].duplicated().any():
        raise ContractError("case_id must be unique in the case table")

    frame = cases.copy()
    for column in ("created_at", "completed_at"):
        frame[column] = pd.to_datetime(frame[column], utc=True, errors="coerce")
        if frame[column].isna().any():
            raise ContractError(f"{column} contains invalid values")
    if (frame["completed_at"] < frame["created_at"]).any():
        raise ContractError("completed_at cannot precede created_at")

    numeric = (
        "amount_usd",
        "event_count",
        "rework_count",
        "cycle_time_hours",
        "sla_target_hours",
    )
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame[list(numeric)].isna().any().any():
        raise ContractError("case numeric fields contain invalid values")
    if (frame[list(numeric)] < 0).any().any():
        raise ContractError("case numeric fields cannot be negative")
    if frame["sla_breached"].dtype == object:
        normalized = frame["sla_breached"].astype(str).str.lower()
        if not normalized.isin({"true", "false", "1", "0"}).all():
            raise ContractError("sla_breached contains invalid boolean values")
        frame["sla_breached"] = normalized.isin({"true", "1"})
    else:
        frame["sla_breached"] = frame["sla_breached"].astype(bool)
    return frame.sort_values("case_id").reset_index(drop=True)


def reconcile_events_and_cases(events: pd.DataFrame, cases: pd.DataFrame) -> None:
    """Require event and case tables to describe the same cases and totals."""

    event_cases = set(events["case_id"].unique())
    case_cases = set(cases["case_id"].unique())
    if event_cases != case_cases:
        missing_from_cases = sorted(event_cases - case_cases)[:5]
        missing_from_events = sorted(case_cases - event_cases)[:5]
        raise ContractError(
            "event and case identifiers differ: "
            f"missing_from_cases={missing_from_cases}, "
            f"missing_from_events={missing_from_events}"
        )

    observed_counts = events.groupby("case_id").size().rename("observed")
    declared_counts = cases.set_index("case_id")["event_count"].rename("declared")
    comparison = pd.concat([observed_counts, declared_counts], axis=1)
    if not (comparison["observed"] == comparison["declared"]).all():
        raise ContractError("event_count does not reconcile to the event log")
