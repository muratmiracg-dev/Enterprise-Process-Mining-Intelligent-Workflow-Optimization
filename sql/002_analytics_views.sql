CREATE OR REPLACE VIEW vw_case_performance AS
SELECT
    c.case_id,
    c.business_unit,
    c.department,
    c.vendor_id,
    c.vendor_tier,
    c.priority,
    c.amount_usd,
    c.variant_ground_truth,
    c.event_count,
    c.rework_count,
    c.cycle_time_hours,
    c.sla_target_hours,
    c.sla_breached,
    ROUND(c.cycle_time_hours / NULLIF(c.sla_target_hours, 0), 4) AS sla_consumption_ratio
FROM process_cases AS c;

CREATE OR REPLACE VIEW vw_activity_performance AS
SELECT
    e.activity,
    COUNT(*) AS event_count,
    COUNT(DISTINCT e.case_id) AS case_count,
    ROUND(AVG(e.processing_minutes), 2) AS mean_processing_minutes,
    ROUND(AVG(CASE WHEN e.automated THEN 1.0 ELSE 0.0 END), 4) AS automation_rate
FROM process_events AS e
GROUP BY e.activity;

CREATE OR REPLACE VIEW vw_sla_performance AS
SELECT
    DATE_TRUNC('month', completed_at) AS completed_month,
    business_unit,
    priority,
    COUNT(*) AS case_count,
    ROUND(AVG(CASE WHEN sla_breached THEN 0.0 ELSE 1.0 END), 4) AS sla_adherence,
    ROUND(AVG(cycle_time_hours), 2) AS mean_cycle_hours,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY cycle_time_hours), 2)
        AS p90_cycle_hours
FROM process_cases
GROUP BY DATE_TRUNC('month', completed_at), business_unit, priority;

CREATE OR REPLACE VIEW vw_directly_follows AS
WITH ordered AS (
    SELECT
        case_id,
        activity,
        event_timestamp,
        LEAD(activity) OVER (
            PARTITION BY case_id ORDER BY event_timestamp, event_index
        ) AS next_activity,
        LEAD(event_timestamp) OVER (
            PARTITION BY case_id ORDER BY event_timestamp, event_index
        ) AS next_timestamp
    FROM process_events
)
SELECT
    activity AS source_activity,
    next_activity AS target_activity,
    COUNT(*) AS transition_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (next_timestamp - event_timestamp)) / 3600), 2)
        AS mean_wait_hours
FROM ordered
WHERE next_activity IS NOT NULL
GROUP BY activity, next_activity;
