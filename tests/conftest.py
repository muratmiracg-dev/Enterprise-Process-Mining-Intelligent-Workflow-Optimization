from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from process_optimizer.repository import EventLogRepository

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def full_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    return EventLogRepository(
        ROOT / "data/demo/p2p_event_log.csv.gz",
        ROOT / "data/demo/case_master.csv.gz",
    ).load()


@pytest.fixture(scope="session")
def sample_frames(
    full_frames: tuple[pd.DataFrame, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events, cases = full_frames
    selected = cases["case_id"].head(1_200)
    return (
        events[events["case_id"].isin(selected)].copy(),
        cases[cases["case_id"].isin(selected)].copy(),
    )


@pytest.fixture
def ideal_events() -> pd.DataFrame:
    activities = ["Start", "Review", "Close"]
    return pd.DataFrame(
        {
            "case_id": ["C-1"] * 3 + ["C-2"] * 4,
            "event_index": [1, 2, 3, 1, 2, 3, 4],
            "activity": activities + ["Start", "Review", "Review", "Close"],
            "timestamp": pd.to_datetime(
                [
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T02:00:00Z",
                    "2026-01-01T03:00:00Z",
                    "2026-01-02T00:00:00Z",
                    "2026-01-02T01:00:00Z",
                    "2026-01-02T04:00:00Z",
                    "2026-01-02T06:00:00Z",
                ],
                utc=True,
            ),
            "resource_id": ["R-1", "R-2", "BOT", "R-1", "R-2", "R-2", "BOT"],
            "resource_role": [
                "Requester",
                "Analyst",
                "Bot",
                "Requester",
                "Analyst",
                "Analyst",
                "Bot",
            ],
            "business_unit": ["BU"] * 7,
            "department": ["Ops"] * 7,
            "country": ["Türkiye"] * 7,
            "vendor_id": ["V-1"] * 7,
            "vendor_tier": ["A"] * 7,
            "material_category": ["MRO"] * 7,
            "amount_usd": [1_000.0] * 7,
            "priority": ["Standard"] * 7,
            "channel": ["Portal"] * 7,
            "automated": [False, False, True, False, False, False, True],
            "processing_minutes": [10.0, 20.0, 1.0, 10.0, 20.0, 20.0, 1.0],
            "source_system": ["ERP"] * 7,
        }
    )
