# ADR-002: Temporal holdout for SLA prediction

**Status:** Accepted — 2026-07-28

## Context

Random splits can overstate performance when process behavior changes over time.

## Decision

Sort cases by creation time, train on the earliest 80%, and evaluate on the
latest 20%. Cut features at Purchase Order creation.

## Consequences

The test more closely resembles future scoring and reduces temporal leakage.
It remains synthetic and cannot establish production generalization.
