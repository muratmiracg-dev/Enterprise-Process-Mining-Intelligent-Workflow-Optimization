# Capacity simulation methodology

## Design

The simulator is a replicated finite-capacity queue network. Each scenario runs
24 replications of 900 cases. The same random seed sequence is reused across
scenarios for more stable paired comparisons.

Capacity-constrained stages:

- Manager Approval
- Procurement Review
- Purchase Order Created
- Goods Received
- Invoice Matched
- Payment Authorized

Service times are lognormal. External supplier/transit lead time enters after
Purchase Order creation. Invoice rework is a scenario-specific probability.

## Scenarios

| Scenario | Intervention | Investment |
|---|---|---:|
| Baseline | Observed staffing and manual assumptions | $0 |
| Approval Automation | Faster low-risk approval and PO preparation | $95,000 |
| AP Capacity | +2 invoice-match and +1 treasury seats | $150,000 |
| Combined Optimization | Automation, AP capacity, supplier intervention | $225,000 |

## Results

| Scenario | Mean cycle | SLA | Annual value | ROI |
|---|---:|---:|---:|---:|
| Baseline | 206.60 h | 64.00% | $0 | 0.00x |
| Approval Automation | 200.12 h | 66.33% | $539,528 | 4.68x |
| AP Capacity | 203.04 h | 65.22% | $185,272 | 0.24x |
| Combined Optimization | 166.48 h | 77.64% | $2,213,037 | 8.84x |

The simulator's baseline is calibrated to process-level distributions, so its
SLA rate need not exactly equal the historical 62.08%.

## Value formula

Annual value combines:

- delay hours saved × $5.50 × 8,000 annual cases;
- manual hours saved × $32 × 8,000;
- breach probability reduction × $85 × 8,000.

First-year ROI is `(annual value - one-time investment) / investment`.

## Interpretation

These are scenario estimates, not booked savings. Before approval, replace all
cost coefficients with Finance-owned values, run sensitivity analysis, and
measure a controlled pilot against a pre-registered baseline.
