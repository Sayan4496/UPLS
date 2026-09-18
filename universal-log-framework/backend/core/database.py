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
                status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
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
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS event_hash VARCHAR(64)"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS duplicate_of UUID"))
        connection.execute(text("ALTER TABLE raw_events ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN NOT NULL DEFAULT FALSE"))

        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS duplicate_of UUID"))
        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_normalized_events_normalized_at_id ON normalized_events (normalized_at, id)"))
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