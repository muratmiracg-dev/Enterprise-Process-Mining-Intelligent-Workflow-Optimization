"""Load the deterministic demo event log into PostgreSQL using COPY."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg

from process_optimizer.config import ProjectPaths, repository_root
from process_optimizer.repository import EventLogRepository


def copy_frame(connection: psycopg.Connection, table: str, frame: pd.DataFrame) -> None:
    columns = list(frame.columns)
    if table == "process_events":
        frame = frame.rename(columns={"timestamp": "event_timestamp"})
        columns = list(frame.columns)
    placeholders = ", ".join(columns)
    with connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {table} CASCADE")  # noqa: S608
        with cursor.copy(f"COPY {table} ({placeholders}) FROM STDIN") as copy:  # noqa: S608
            for row in frame.itertuples(index=False, name=None):
                copy.write_row(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://process_app:local-development-only@localhost:5432/process_intelligence",
        ),
    )
    parser.add_argument("--root", type=Path, default=repository_root())
    args = parser.parse_args()
    paths = ProjectPaths(args.root.resolve())
    events, cases = EventLogRepository(paths.event_log, paths.cases).load()

    with psycopg.connect(args.database_url) as connection:
        copy_frame(connection, "process_cases", cases)
        copy_frame(connection, "process_events", events)
        connection.commit()
    print(f"Loaded {len(cases):,} cases and {len(events):,} events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
