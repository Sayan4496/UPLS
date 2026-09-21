import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


DATABASE_URL = os.getenv("DATABASE_URL")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def ensure_database_schema():
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS processing_jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                status VARCHAR(20) NOT NULL DEFAULT 'queued',
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
            )
        """))
        connection.execute(text("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS details JSONB NOT NULL DEFAULT '[]'::jsonb"))
        connection.execute(text("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS processing_time DOUBLE PRECISION NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS message_id VARCHAR(100)"))
        connection.execute(text("ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS queue_offset BIGINT"))
        connection.execute(text("UPDATE processing_jobs SET status = LOWER(status) WHERE status IN ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS event_hash VARCHAR(64)"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS duplicate_of UUID"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) NOT NULL DEFAULT 'RECEIVED'"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS status_reason TEXT"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS universal_event JSONB"))

        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS duplicate_of UUID"))
        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) NOT NULL DEFAULT 'ACCEPTED'"))
        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS status_reason TEXT"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_normalized_events_normalized_at_id ON normalized_events (normalized_at, id)"))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS feature_source_rollups (
                source_type VARCHAR(50) NOT NULL,
                window_start TIMESTAMPTZ NOT NULL,
                event_count INTEGER NOT NULL,
                PRIMARY KEY (source_type, window_start)
            )
        """))
        connection.execute(text("""
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
            )
        """))
        # Upgrade the Phase 7 table in place. Existing deployments may have
        # the legacy feature columns from an earlier initializer.
        connection.execute(text(
            "ALTER TABLE normalized_event_features "
            "ADD COLUMN IF NOT EXISTS source_type VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN'"
        ))
        connection.execute(text(
            "ALTER TABLE normalized_event_features "
            "ADD COLUMN IF NOT EXISTS source_event_count_24h INTEGER NOT NULL DEFAULT 0"
        ))
        connection.execute(text(
            "ALTER TABLE normalized_event_features "
            "ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        ))
        connection.execute(text("""
            UPDATE normalized_event_features AS features
            SET source_type = COALESCE(events.source_format, 'UNKNOWN')
            FROM normalized_events AS events
            WHERE events.id = features.event_id
        """))
        connection.execute(text("""
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
        """))
        connection.execute(text(
            "ALTER TABLE normalized_event_features "
            "ALTER COLUMN feature_schema_version SET DEFAULT '1.0.0'"
        ))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS datalake_export_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status VARCHAR(20) NOT NULL DEFAULT 'idle',
                last_run_at TIMESTAMPTZ,
                last_error TEXT,
                rows_exported BIGINT NOT NULL DEFAULT 0,
                watermark_normalized_at TIMESTAMPTZ,
                watermark_id UUID,
                partition_count INTEGER NOT NULL DEFAULT 0
            )
        """))
        connection.execute(text("ALTER TABLE datalake_export_state ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'idle'"))
        connection.execute(text("ALTER TABLE datalake_export_state ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE datalake_export_state ADD COLUMN IF NOT EXISTS watermark_normalized_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE datalake_export_state ADD COLUMN IF NOT EXISTS watermark_id UUID"))
        connection.execute(text("ALTER TABLE datalake_export_state ADD COLUMN IF NOT EXISTS partition_count INTEGER NOT NULL DEFAULT 0"))
        connection.execute(text("ALTER TABLE datalake_export_state ADD COLUMN IF NOT EXISTS partition_coverage JSONB NOT NULL DEFAULT '[]'::jsonb"))
        connection.execute(text("""
            UPDATE datalake_export_state
            SET last_run_at = COALESCE(last_run_at, last_export_at),
                watermark_normalized_at = COALESCE(watermark_normalized_at, last_exported_normalized_at),
                watermark_id = COALESCE(watermark_id, last_exported_id),
                partition_count = CASE
                    WHEN partition_count = 0 THEN jsonb_array_length(partition_coverage)
                    ELSE partition_count
                END
            WHERE id = 1
        """))
        connection.execute(text("""
            INSERT INTO datalake_export_state (id)
            VALUES (1)
            ON CONFLICT (id) DO NOTHING
        """))


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()