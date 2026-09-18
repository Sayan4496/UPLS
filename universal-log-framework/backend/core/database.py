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

        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS duplicate_of UUID"))
        connection.execute(text("ALTER TABLE normalized_events ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN NOT NULL DEFAULT FALSE"))


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()