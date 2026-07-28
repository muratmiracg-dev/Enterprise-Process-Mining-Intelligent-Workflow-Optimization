CREATE TABLE IF NOT EXISTS process_cases (
    case_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    business_unit TEXT NOT NULL,
    department TEXT NOT NULL,
    country TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_tier TEXT NOT NULL CHECK (vendor_tier IN ('A', 'B', 'C')),
    material_category TEXT NOT NULL,
    amount_usd NUMERIC(14, 2) NOT NULL CHECK (amount_usd >= 0),
    priority TEXT NOT NULL CHECK (priority IN ('Urgent', 'Standard', 'Strategic')),
    channel TEXT NOT NULL,
    variant_ground_truth TEXT NOT NULL,
    event_count INTEGER NOT NULL CHECK (event_count > 0),
    rework_count INTEGER NOT NULL CHECK (rework_count >= 0),
    cycle_time_hours NUMERIC(14, 4) NOT NULL CHECK (cycle_time_hours >= 0),
    sla_target_hours NUMERIC(10, 2) NOT NULL CHECK (sla_target_hours > 0),
    sla_breached BOOLEAN NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS process_events (
    case_id TEXT NOT NULL REFERENCES process_cases(case_id) ON DELETE CASCADE,
    event_index INTEGER NOT NULL,
    activity TEXT NOT NULL,
    event_timestamp TIMESTAMPTZ NOT NULL,
    resource_id TEXT NOT NULL,
    resource_role TEXT NOT NULL,
    business_unit TEXT NOT NULL,
    department TEXT NOT NULL,
    country TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    vendor_tier TEXT NOT NULL,
    material_category TEXT NOT NULL,
    amount_usd NUMERIC(14, 2) NOT NULL,
    priority TEXT NOT NULL,
    channel TEXT NOT NULL,
    automated BOOLEAN NOT NULL,
    processing_minutes NUMERIC(12, 2) NOT NULL CHECK (processing_minutes >= 0),
    source_system TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (case_id, event_index)
);

CREATE INDEX IF NOT EXISTS idx_process_events_timestamp
    ON process_events (event_timestamp);
CREATE INDEX IF NOT EXISTS idx_process_events_activity
    ON process_events (activity);
CREATE INDEX IF NOT EXISTS idx_process_events_vendor
    ON process_events (vendor_id, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_process_cases_sla
    ON process_cases (sla_breached, completed_at);
