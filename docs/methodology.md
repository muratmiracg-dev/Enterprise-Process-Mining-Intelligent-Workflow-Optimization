# Analytical methodology

## 1. Process scope

The case is one Purchase-to-Pay request, from `Purchase Request Created` through
`Case Closed`. The designed path contains 13 activities. The generator also
creates realistic exception variants: approval rework, missing approval,
delivery delay, invoice discrepancy, three-way-match failure, duplicate invoice,
and payment rework.

## 2. Synthetic data

- Seed: `20260728`
- Cases: 12,000
- Events: 166,551
- Window: 2025-01-01 to 2026-07-17 UTC
- Vendors: 80 synthetic IDs
- Operational resources: 150 synthetic IDs

Amounts use a capped lognormal distribution. Transition and processing times
vary by amount, priority, vendor tier, country, and activity. All names and
outcomes are fictional.

## 3. Discovery

Case traces are ordered by case, timestamp, and event index. The platform
calculates:

- variants and case share;
- directly-follows frequency and wait distributions;
- activity volume, reach, automation, and processing time;
- PM4Py DFG and inductive process-tree reference output.

## 4. Conformance

Each observed trace is compared with the ideal path using Levenshtein edit
distance. Fitness is:

`1 - edit_distance / max(observed_length, ideal_length, 1)`.

The output separately records missing, unexpected, and repeated activities.
This transparent score complements PM4Py; it is not claimed to replace
token-replay or alignment fitness for every production use case.

## 5. Performance and rework

Wait is the timestamp difference between consecutive events. Estimated case
wait is cycle time minus recorded processing time, floored at zero. The
bottleneck score combines normalized total wait (55%), p90 wait (30%), and case
coverage (15%). Weights are a management prioritization heuristic.

## 6. SLA prediction

Features are cut at Purchase Order creation to avoid future leakage. Cases are
sorted chronologically; the first 80% train the logistic regression and the
latest 20% form an untouched temporal holdout. See the model card.

## 7. Capacity simulation

Four scenarios use the same replication seeds to reduce comparison noise.
Results represent modeled interventions, not causal proof. See the simulation
methodology for queue capacities, service assumptions, and value formula.

## 8. Reproducibility

CSV field order, row order, random seed, timestamps, numerical formatting, and
gzip metadata are fixed. CI regenerates and compares the compressed event and
case files byte-for-byte.
