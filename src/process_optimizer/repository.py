"""Repository adapters for local analytical datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from process_optimizer.contracts import (
    reconcile_events_and_cases,
    validate_cases,
    validate_event_log,
)


@dataclass(frozen=True)
class EventLogRepository:
    """Read deterministic CSV-backed process data."""

    event_log_path: Path
    case_path: Path

    def load(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        events = validate_event_log(pd.read_csv(self.event_log_path))
        cases = validate_cases(pd.read_csv(self.case_path))
        reconcile_events_and_cases(events, cases)
        return events, cases
