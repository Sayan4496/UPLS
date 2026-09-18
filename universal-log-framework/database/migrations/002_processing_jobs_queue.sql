BEGIN;

ALTER TABLE processing_jobs
    ADD COLUMN IF NOT EXISTS message_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS queue_offset BIGINT;

UPDATE processing_jobs
SET status = LOWER(status)
WHERE status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED');

ALTER TABLE processing_jobs
    ALTER COLUMN status SET DEFAULT 'queued';

COMMIT;
