-- ============================================================
-- Universal Log Pre-processing Framework (ULPF)
-- Database initialization script
-- ============================================================

-- Needed for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_event_id      UUID NOT NULL REFERENCES raw_events (id) ON DELETE CASCADE,
    event_timestamp   TIMESTAMPTZ,
    source_ip         INET,
    destination_ip    INET,
    source_port       INTEGER CHECK (source_port BETWEEN 0 AND 65535),
    destination_port  INTEGER CHECK (destination_port BETWEEN 0 AND 65535),
    severity          VARCHAR(20),   -- e.g. LOW, MEDIUM, HIGH, CRITICAL
    event_type        VARCHAR(100),
    action            VARCHAR(50),   -- e.g. ALLOW, DENY, DROP, ALERT
    device_type       VARCHAR(50),   -- e.g. FIREWALL, IDS, VPN, ROUTER
    vendor            VARCHAR(50),   -- e.g. PFSENSE, FORTIGATE, SURICATA
    message           TEXT,
    normalized_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Traceability: always be able to jump from a normalized event to its raw original
CREATE INDEX IF NOT EXISTS idx_normalized_events_raw_event_id ON normalized_events (raw_event_id);

-- Query/filter patterns from the Search & Analytics API
CREATE INDEX IF NOT EXISTS idx_normalized_events_timestamp ON normalized_events (event_timestamp);
CREATE INDEX IF NOT EXISTS idx_normalized_events_source_ip ON normalized_events (source_ip);
CREATE INDEX IF NOT EXISTS idx_normalized_events_destination_ip ON normalized_events (destination_ip);
CREATE INDEX IF NOT EXISTS idx_normalized_events_severity ON normalized_events (severity);
CREATE INDEX IF NOT EXISTS idx_normalized_events_device_type ON normalized_events (device_type);
CREATE INDEX IF NOT EXISTS idx_normalized_events_vendor ON normalized_events (vendor);