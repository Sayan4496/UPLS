BEGIN;

-- Phase 7 may already have created normalized_event_features with the legacy
-- feature columns. Upgrade it in place and preserve every existing row.
ALTER TABLE normalized_event_features
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    ADD COLUMN IF NOT EXISTS source_event_count_24h INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ NOT NULL DEFAULT now();

UPDATE normalized_event_features AS features
SET source_type = COALESCE(events.source_format, 'UNKNOWN')
FROM normalized_events AS events
WHERE events.id = features.event_id;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'normalized_event_features'
          AND column_name = 'rolling_source_event_count'
    ) THEN
        EXECUTE 'UPDATE normalized_event_features
                 SET source_event_count_24h = COALESCE(
                     NULLIF(rolling_source_event_count, 0),
                     NULLIF(source_event_count_1h, 0),
                     0
                 )';
    END IF;
END $$;

ALTER TABLE normalized_event_features
    ALTER COLUMN feature_schema_version SET DEFAULT '1.0.0';

COMMIT;