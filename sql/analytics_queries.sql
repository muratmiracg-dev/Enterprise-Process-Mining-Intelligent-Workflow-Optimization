-- Highest waiting-time transitions
SELECT source_activity, target_activity, transition_count, mean_wait_hours
FROM vw_directly_follows
ORDER BY mean_wait_hours * transition_count DESC
LIMIT 15;

-- Business units with the largest SLA performance gap
SELECT
    business_unit,
    COUNT(*) AS cases,
    ROUND(AVG(CASE WHEN sla_breached THEN 0.0 ELSE 1.0 END), 4) AS sla_adherence,
    ROUND(AVG(cycle_time_hours), 2) AS mean_cycle_hours
FROM process_cases
GROUP BY business_unit
ORDER BY sla_adherence;

-- Rework concentration
SELECT variant_ground_truth, COUNT(*) AS cases, SUM(rework_count) AS repeat_events
FROM process_cases
WHERE rework_count > 0
GROUP BY variant_ground_truth
ORDER BY repeat_events DESC;
