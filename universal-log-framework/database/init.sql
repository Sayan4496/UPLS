-- ============================================================
-- Universal Log Pre-processing Framework (ULPF)
-- Database initialization script
-- ============================================================

-- Needed for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =========================
-- Processing Jobs
-- =========================

CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    message_id VARCHAR(100),
    queue_offset BIGINT,
    total_files INTEGER NOT NULL DEFAULT 0,
    processed_files INTEGER NOT NULL DEFAULT 0,
    failed_files INTEGER NOT NULL DEFAULT 0,
    total_records INTEGER NOT NULL DEFAULT 0,
    processed_records INTEGER NOT NULL DEFAULT 0,
    failed_records INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    details JSONB NOT NULL DEFAULT '[]'::jsonb,
    processing_time DOUBLE PRECISION NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================
-- Uploads Table
-- =========================

CREATE TABLE uploads (

    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    filename VARCHAR(255) NOT NULL,

    file_type VARCHAR(50) NOT NULL,

    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);


-- ------------------------------------------------------------
-- raw_events
-- Immutable store of every log exactly as it was received.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_events (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id        UUID NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    event_hash       VARCHAR(64),
    duplicate_of     UUID NULL REFERENCES raw_events(id) ON DELETE SET NULL,
    is_duplicate     BOOLEAN NOT NULL DEFAULT FALSE,
    processing_status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED',
    status_reason     TEXT,
    universal_event   JSONB,
    raw_content      TEXT NOT NULL,
    original_format  VARCHAR(20) NOT NULL,   -- JSON, SYSLOG, CSV, KEY-VALUE, CEF, NETFLOW, UNKNOWN
    checksum         VARCHAR(64) NOT NULL,   -- SHA-256 hex digest of raw_content
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_events_upload_id ON raw_events (upload_id);
CREATE INDEX IF NOT EXISTS idx_raw_events_created_at ON raw_events (created_at);
CREATE INDEX IF NOT EXISTS idx_raw_events_checksum ON raw_events (checksum);

-- ------------------------------------------------------------
-- normalized_events
-- One standardized, queryable record per raw event.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS normalized_events (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_event_id         UUID NOT NULL REFERENCES raw_events (id) ON DELETE CASCADE,
    upload_id            UUID NOT NULL REFERENCES uploads(id) ON DELETE CASCADE,
    event_hash           VARCHAR(64) NOT NULL,
    duplicate_of         UUID NULL REFERENCES normalized_events(id) ON DELETE SET NULL,
    is_duplicate         BOOLEAN NOT NULL DEFAULT FALSE,
    processing_status     VARCHAR(20) NOT NULL DEFAULT 'ACCEPTED',
    status_reason         TEXT,
    parsed_log           JSONB NOT NULL,
    normalized_log       JSONB NOT NULL,
    universal_event      JSONB,
    parser_used          VARCHAR(100) NOT NULL,
    parser_version       VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    normalization_version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    source_format        VARCHAR(20) NOT NULL,
    parser_confidence    DOUBLE PRECISION NOT NULL,
    fallback_used        BOOLEAN NOT NULL DEFAULT FALSE,
    parser_metadata      JSONB NOT NULL,
    quality_metrics      JSONB,
    processing_history   JSONB,
    processing_time      DOUBLE PRECISION NOT NULL,
    processing_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_timestamp      TIMESTAMPTZ,
    source_ip            INET,
    destination_ip       INET,
    source_port          INTEGER CHECK (source_port BETWEEN 0 AND 65535),
    destination_port     INTEGER CHECK (destination_port BETWEEN 0 AND 65535),
    severity             VARCHAR(20),   -- e.g. LOW, MEDIUM, HIGH, CRITICAL
    event_type           VARCHAR(100),
    action               VARCHAR(50),   -- e.g. ALLOW, DENY, DROP, ALERT
    device_type          VARCHAR(50),   -- e.g. FIREWALL, IDS, VPN, ROUTER
    vendor               VARCHAR(50),   -- e.g. PFSENSE, FORTIGATE, SURICATA
    message              TEXT,
    normalized_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Traceability: always be able to jump from a normalized event to its raw original
CREATE INDEX IF NOT EXISTS idx_normalized_events_raw_event_id ON normalized_events (raw_event_id);
CREATE INDEX IF NOT EXISTS idx_normalized_events_upload_id ON normalized_events (upload_id);
CREATE INDEX IF NOT EXISTS idx_normalized_events_event_hash ON normalized_events (event_hash);
CREATE UNIQUE INDEX IF NOT EXISTS uq_normalized_events_canonical_event_hash
    ON normalized_events (event_hash)
    WHERE is_duplicate = FALSE;

-- Query/filter patterns from the Search & Analytics API
CREATE INDEX IF NOT EXISTS idx_normalized_events_timestamp ON normalized_events (event_timestamp);
CREATE INDEX IF NOT EXISTS idx_normalized_events_source_ip ON normalized_events (source_ip);
CREATE INDEX IF NOT EXISTS idx_normalized_events_destination_ip ON normalized_events (destination_ip);
CREATE INDEX IF NOT EXISTS idx_normalized_events_severity ON normalized_events (severity);
CREATE INDEX IF NOT EXISTS idx_normalized_events_device_type ON normalized_events (device_type);
CREATE INDEX IF NOT EXISTS idx_normalized_events_vendor ON normalized_events (vendor);
CREATE INDEX IF NOT EXISTS idx_normalized_events_normalized_at_id ON normalized_events (normalized_at, id);

CREATE TABLE IF NOT EXISTS feature_source_rollups (
    source_type  VARCHAR(50) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    event_count  INTEGER NOT NULL,
    PRIMARY KEY (source_type, window_start)
);

CREATE TABLE IF NOT EXISTS normalized_event_features (
    event_id               UUID PRIMARY KEY REFERENCES normalized_events(id) ON DELETE CASCADE,
    feature_schema_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    source_type            VARCHAR(50) NOT NULL,
    source_type_code       INTEGER NOT NULL,
    severity_code          INTEGER NOT NULL,
    action_code            INTEGER NOT NULL,
    event_hour             INTEGER NOT NULL,
    event_day_of_week      INTEGER NOT NULL,
    source_event_count_24h INTEGER NOT NULL,
    generated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS datalake_export_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    status VARCHAR(20) NOT NULL DEFAULT 'idle',
    last_run_at TIMESTAMPTZ,
    last_error TEXT,
    rows_exported BIGINT NOT NULL DEFAULT 0,
    watermark_normalized_at TIMESTAMPTZ,
    watermark_id UUID,
    partition_count INTEGER NOT NULL DEFAULT 0,
    partition_coverage JSONB NOT NULL DEFAULT '[]'::jsonb
);

INSERT INTO datalake_export_state (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- Existing installations can apply the metadata columns without replacing data.
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS raw_event_id UUID;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS upload_id UUID;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS event_hash VARCHAR(64);
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS parsed_log JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS normalized_log JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS universal_event JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS parser_used VARCHAR(100);
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS parser_version VARCHAR(50) DEFAULT '1.0.0';
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS normalization_version VARCHAR(50) DEFAULT '1.0.0';
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS source_format VARCHAR(20);
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS parser_confidence DOUBLE PRECISION;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN DEFAULT FALSE;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS parser_metadata JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS quality_metrics JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS processing_history JSONB;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS processing_time DOUBLE PRECISION;
ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS processing_timestamp TIMESTAMPTZ DEFAULT now();