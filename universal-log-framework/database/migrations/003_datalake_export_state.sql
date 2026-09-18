BEGIN;

CREATE INDEX IF NOT EXISTS idx_normalized_events_normalized_at_id
    ON normalized_events (normalized_at, id);

CREATE TABLE IF NOT EXISTS datalake_export_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status VARCHAR(20) NOT NULL DEFAULT 'idle',
    last_run_at TIMESTAMPTZ,
    last_error TEXT,
    rows_exported BIGINT NOT NULL DEFAULT 0,
    watermark_normalized_at TIMESTAMPTZ,
    watermark_id UUID,
    partition_count INTEGER NOT NULL DEFAULT 0
);

ALTER TABLE datalake_export_state
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'idle',
    ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS watermark_normalized_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS watermark_id UUID,
    ADD COLUMN IF NOT EXISTS partition_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS partition_coverage JSONB NOT NULL DEFAULT '[]'::jsonb;

UPDATE datalake_export_state
SET last_run_at = COALESCE(last_run_at, last_export_at),
    watermark_normalized_at = COALESCE(watermark_normalized_at, last_exported_normalized_at),
    watermark_id = COALESCE(watermark_id, last_exported_id),
    partition_count = CASE
        WHEN partition_count = 0 THEN jsonb_array_length(partition_coverage)
        ELSE partition_count
    END
WHERE id = 1;

INSERT INTO datalake_export_state (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

COMMIT;