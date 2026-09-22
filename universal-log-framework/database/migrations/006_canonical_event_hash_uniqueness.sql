BEGIN;

UPDATE normalized_events
SET processing_status = 'DUPLICATE'
WHERE is_duplicate = TRUE
  AND LOWER(processing_status) = 'accepted';

ALTER TABLE normalized_events
    DROP CONSTRAINT IF EXISTS uq_normalized_events_event_hash,
    DROP CONSTRAINT IF EXISTS normalized_events_event_hash_key;

DROP INDEX IF EXISTS uq_normalized_events_event_hash;

CREATE UNIQUE INDEX IF NOT EXISTS uq_normalized_events_canonical_event_hash
    ON normalized_events (event_hash)
    WHERE is_duplicate = FALSE;

COMMIT;