# ADR-001: Versioned CSV benchmark as analytical system of record

**Status:** Accepted — 2026-07-28

## Context

The portfolio project needs reproducibility, code review, and zero external
infrastructure for reviewers.

## Decision

Use deterministic compressed CSV files as the committed benchmark. PostgreSQL is
a deployment adapter, not the source of truth for acceptance.

## Consequences

Reviewers can reproduce every metric locally. CSV is not intended for
high-concurrency production workloads; production ingestion should use governed
object storage and database tables.
