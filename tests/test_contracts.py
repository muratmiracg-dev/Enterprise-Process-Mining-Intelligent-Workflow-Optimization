from __future__ import annotations

import pandas as pd
import pytest

from process_optimizer.contracts import (
    CASE_COLUMNS,
    ContractError,
    reconcile_events_and_cases,
    validate_cases,
    validate_event_log,
)


def _case_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "case_id": "C-1",
                "created_at": "2026-01-01T00:00:00Z",
                "completed_at": "2026-01-01T02:00:00Z",
                "business_unit": "BU",
                "department": "Ops",
                "country": "Türkiye",
                "vendor_id": "V-1",
                "vendor_tier": "A",
                "material_category": "MRO",
                "amount_usd": "100",
                "priority": "Standard",
                "channel": "Portal",
                "variant_ground_truth": "happy",
                "event_count": "2",
                "rework_count": "0",
                "cycle_time_hours": "2",
                "sla_target_hours": "24",
                "sla_breached": "false",
            }
        ]
    )


def _event_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "case_id": "C-1",
                "event_index": 1,
                "activity": "Start",
                "timestamp": "2026-01-01T00:00:00Z",
                "resource_id": "R-1",
                "resource_role": "Requester",
                "business_unit": "BU",
                "department": "Ops",
                "country": "Türkiye",
                "vendor_id": "V-1",
                "vendor_tier": "A",
                "material_category": "MRO",
                "amount_usd": "100",
                "priority": "Standard",
                "channel": "Portal",
                "automated": "false",
                "processing_minutes": "5",
                "source_system": "ERP",
            },
            {
                "case_id": "C-1",
                "event_index": 2,
                "activity": "Close",
                "timestamp": "2026-01-01T02:00:00Z",
                "resource_id": "BOT",
                "resource_role": "Bot",
                "business_unit": "BU",
                "department": "Ops",
                "country": "Türkiye",
                "vendor_id": "V-1",
                "vendor_tier": "A",
                "material_category": "MRO",
                "amount_usd": "100",
                "priority": "Standard",
                "channel": "Portal",
                "automated": "1",
                "processing_minutes": "1",
                "source_system": "ERP",
            },
        ]
    )


def test_validate_event_log_normalizes_types() -> None:
    result = validate_event_log(_event_frame().iloc[::-1])
    assert str(result["timestamp"].dtype) == "datetime64[ns, UTC]"
    assert result["automated"].tolist() == [False, True]
    assert result["event_index"].tolist() == [1, 2]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.drop(columns=["activity"]), "missing required"),
        (lambda frame: frame.iloc[0:0], "at least one event"),
        (lambda frame: frame.assign(activity=None), "cannot contain null"),
        (lambda frame: frame.assign(timestamp="bad"), "invalid values"),
        (lambda frame: frame.assign(event_index="bad"), "event_index"),
        (lambda frame: frame.assign(amount_usd=-1), "cannot be negative"),
        (lambda frame: frame.assign(automated="maybe"), "boolean"),
    ],
)
def test_validate_event_log_rejects_invalid_inputs(mutation, message: str) -> None:
    with pytest.raises(ContractError, match=message):
        validate_event_log(mutation(_event_frame()))


def test_validate_event_log_rejects_duplicate_key() -> None:
    frame = pd.concat([_event_frame(), _event_frame().iloc[[0]]], ignore_index=True)
    with pytest.raises(ContractError, match="must be unique"):
        validate_event_log(frame)


def test_validate_cases_normalizes_types() -> None:
    result = validate_cases(_case_frame())
    assert tuple(column for column in CASE_COLUMNS if column not in result) == ()
    assert result.loc[0, "sla_breached"] == False  # noqa: E712
    assert result.loc[0, "cycle_time_hours"] == 2


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda frame: frame.drop(columns=["country"]), "missing required"),
        (lambda frame: frame.iloc[0:0], "at least one case"),
        (
            lambda frame: pd.concat([frame, frame], ignore_index=True),
            "case_id must be unique",
        ),
        (lambda frame: frame.assign(created_at="bad"), "created_at"),
        (
            lambda frame: frame.assign(completed_at="2025-01-01T00:00:00Z"),
            "cannot precede",
        ),
        (lambda frame: frame.assign(event_count="bad"), "numeric"),
        (lambda frame: frame.assign(cycle_time_hours=-1), "cannot be negative"),
        (lambda frame: frame.assign(sla_breached="maybe"), "boolean"),
    ],
)
def test_validate_cases_rejects_invalid_inputs(mutation, message: str) -> None:
    with pytest.raises(ContractError, match=message):
        validate_cases(mutation(_case_frame()))


def test_reconcile_accepts_matching_frames() -> None:
    reconcile_events_and_cases(
        validate_event_log(_event_frame()),
        validate_cases(_case_frame()),
    )


def test_reconcile_rejects_identifier_mismatch() -> None:
    cases = validate_cases(_case_frame().assign(case_id="C-2"))
    with pytest.raises(ContractError, match="identifiers differ"):
        reconcile_events_and_cases(validate_event_log(_event_frame()), cases)


def test_reconcile_rejects_count_mismatch() -> None:
    cases = validate_cases(_case_frame().assign(event_count=3))
    with pytest.raises(ContractError, match="does not reconcile"):
        reconcile_events_and_cases(validate_event_log(_event_frame()), cases)
