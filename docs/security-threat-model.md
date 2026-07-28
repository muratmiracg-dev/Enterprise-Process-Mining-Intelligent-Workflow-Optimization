# Security threat model

## Assets

Process event history, supplier dimensions, transaction values, risk scores,
model artifacts, credentials, dashboards, and audit evidence.

## Threats and controls

| Threat | Control | Residual risk |
|---|---|---|
| Malformed event data | Strict contracts and reconciliation | Valid but misleading data |
| Credential disclosure | Environment variables and secret scanning | Local default misuse |
| Unauthorized mutation | Read-only API and no payment integration | Future adapter scope creep |
| Container breakout | Nonroot, dropped capabilities, read-only filesystem | Runtime vulnerability |
| SQL injection | Fixed table targets and parameterized app queries | Future dynamic SQL |
| Model misuse | Model card, governance route, human review | Automation bias |
| Dashboard overexposure | Deployment requires access control | Exported-file leakage |
| Dependency compromise | Pinned Actions, Dependabot, CodeQL, Trivy | Zero-day risk |
| Data poisoning | Quality checks and versioned benchmarks | Plausible adversarial inputs |

## Data classification

Committed data is synthetic and public. Real procurement events would be
confidential and could contain commercially sensitive supplier, employee, and
payment information. The repository is not a permitted production data store.

## Abuse prevention

The platform must never:

- autonomously approve a purchase request;
- reject an invoice or vendor based only on model score;
- authorize or execute payment;
- infer employee performance without reviewed context;
- bypass segregation of duties.
