# Data contracts

## Event log

Primary key: `(case_id, event_index)`.

| Field | Type | Rule |
|---|---|---|
| `case_id` | string | Required, reconciles to case master |
| `event_index` | integer | Required, unique within case |
| `activity` | string | Required |
| `timestamp` | UTC datetime | Required, monotonic within case |
| `resource_id` | string | Synthetic actor or bot |
| `resource_role` | string | Controlled role label |
| `business_unit`, `department`, `country` | string | Case dimensions |
| `vendor_id`, `vendor_tier` | string | Synthetic supplier dimensions |
| `material_category` | string | Spend category |
| `amount_usd` | decimal | Nonnegative |
| `priority`, `channel` | string | Workflow dimensions |
| `automated` | boolean | Normalized from true/false/1/0 |
| `processing_minutes` | decimal | Nonnegative |
| `source_system` | string | Synthetic lineage label |

## Case master

Primary key: `case_id`.

| Field | Type | Rule |
|---|---|---|
| `created_at`, `completed_at` | UTC datetime | Completion cannot precede creation |
| `variant_ground_truth` | string | Generator-only benchmark label |
| `event_count` | integer | Must equal observed event count |
| `rework_count` | integer | Nonnegative |
| `cycle_time_hours` | decimal | Nonnegative |
| `sla_target_hours` | decimal | Urgent 120, Standard 240, Strategic 336 |
| `sla_breached` | boolean | Cycle time exceeds target |

## Quality gates

- identical event and case identifier sets;
- zero duplicate primary keys;
- zero null case/activity/timestamp values;
- valid UTC timestamps;
- monotonic event timestamps per case;
- nonnegative amounts and durations;
- declared and observed event counts reconcile.
