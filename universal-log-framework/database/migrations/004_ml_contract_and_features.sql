BEGIN;

ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED';
ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS status_reason TEXT;
ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS universal_event JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) NOT NULL DEFAULT 'ACCEPTED';
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS status_reason TEXT;

CREATE TABLE IF NOT EXISTS feature_source_rollups (
    source_type VARCHAR(50) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    event_count INTEGER NOT NULL,
    PRIMARY KEY (source_type, window_start)
);

CREATE TABLE IF NOT EXISTS normalized_event_features (
    event_id UUID PRIMARY KEY REFERENCES normalized_events(id) ON DELETE CASCADE,
    feature_schema_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    source_type VARCHAR(50) NOT NULL,
    source_type_code INTEGER NOT NULL,
    severity_code INTEGER NOT NULL,
    action_code INTEGER NOT NULL,
    event_hour INTEGER NOT NULL,
    event_day_of_week INTEGER NOT NULL,
    source_event_count_24h INTEGER NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;