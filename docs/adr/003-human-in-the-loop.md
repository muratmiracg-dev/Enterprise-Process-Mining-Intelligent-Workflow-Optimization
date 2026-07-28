# ADR-003: Human-in-the-loop decision boundary

**Status:** Accepted — 2026-07-28

## Context

Purchase approval, invoice exception handling, and payment authorization are
material business controls.

## Decision

Expose only read-only analytics and recommendations. Risk scores prioritize
review; no endpoint mutates a transaction or executes a payment.

## Consequences

Automation benefits are modeled without weakening accountability or segregation
of duties. A future workflow integration requires a new security and control ADR.
