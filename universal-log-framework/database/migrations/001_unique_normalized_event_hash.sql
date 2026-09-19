-- Enforce one canonical normalized event per fingerprint.
-- Run this migration during a maintenance window because the cleanup and
-- constraint acquisition require locks on normalized_events.

BEGIN;

-- Audit query: review the rows that must be deduplicated before the constraint.
SELECT
    event_hash,
    COUNT(*) AS duplicate_count,
    ARRAY_AGG(id ORDER BY processing_timestamp NULLS LAST, id) AS normalized_event_ids
FROM normalized_events
GROUP BY event_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, event_hash;

-- Keep the earliest normalized row for each fingerprint. All other rows are
-- removed after their raw and self-referential normalized links are rewired.
CREATE TEMP TABLE normalized_event_deduplication ON COMMIT DROP AS
WITH ranked_events AS (
    SELECT
        id,
        raw_event_id,
        event_hash,
        ROW_NUMBER() OVER (
            PARTITION BY event_hash
            ORDER BY processing_timestamp NULLS LAST, id
        ) AS row_number
    FROM normalized_events
)
SELECT
    duplicate.id AS duplicate_id,
    duplicate.raw_event_id AS duplicate_raw_event_id,
    keeper.id AS keeper_id,
    keeper.raw_event_id AS keeper_raw_event_id
FROM ranked_events AS duplicate
JOIN ranked_events AS keeper
  ON keeper.event_hash = duplicate.event_hash
 AND keeper.row_number = 1
WHERE duplicate.row_number > 1;

UPDATE raw_events AS raw_event
SET
    duplicate_of = dedup.keeper_raw_event_id,
    is_duplicate = TRUE
FROM normalized_event_deduplication AS dedup
WHERE raw_event.id = dedup.duplicate_raw_event_id;

UPDATE normalized_events AS normalized_event
SET
    duplicate_of = dedup.keeper_id,
    is_duplicate = TRUE
FROM normalized_event_deduplication AS dedup
WHERE normalized_event.duplicate_of = dedup.duplicate_id;

DELETE FROM normalized_events AS normalized_event
USING normalized_event_deduplication AS dedup
WHERE normalized_event.id = dedup.duplicate_id;

DROP INDEX IF EXISTS idx_normalized_events_event_hash;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_normalized_events_event_hash'
          AND conrelid = 'normalized_events'::regclass
    ) THEN
        ALTER TABLE normalized_events
            ADD CONSTRAINT uq_normalized_events_event_hash UNIQUE (event_hash);
    END IF;
END
$$;

COMMIT;
