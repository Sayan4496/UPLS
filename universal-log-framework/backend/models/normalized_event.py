import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    Float,
    Boolean
)
from sqlalchemy.orm import synonym

from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.sql import func

from core.database import Base


class NormalizedEvent(Base):

    __tablename__ = "normalized_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    raw_event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_events.id", ondelete="CASCADE"),
        nullable=False
    )

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id", ondelete="CASCADE"),
        nullable=False
    )

    event_hash = Column(
        String(64),
        nullable=False
    )

    parsed_log = Column(
        JSONB,
        nullable=False
    )

    normalized_log = Column(
        JSONB,
        nullable=False
    )

    universal_event = Column(
        JSONB,
        nullable=True
    )

    normalized_data = synonym("normalized_log")

    parser_used = Column(
        String(100),
        nullable=False
    )

    parser_version = Column(
        String(50),
        nullable=False,
        default="1.0.0"
    )

    normalization_version = Column(
        String(50),
        nullable=False,
        default="1.0.0"
    )

    source_format = Column(
        String(20),
        nullable=False
    )

    parser_confidence = Column(
        Float,
        nullable=False
    )

    fallback_used = Column(
        Boolean,
        nullable=False,
        default=False
    )

    parser_metadata = Column(
        JSONB,
        nullable=False
    )

    quality_metrics = Column(
        JSONB,
        nullable=True
    )

    processing_history = Column(
        JSONB,
        nullable=True
    )

    processing_time = Column(
        Float,
        nullable=False
    )

    processing_timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    event_timestamp = Column(
        DateTime(timezone=True),
        nullable=True
    )

    source_ip = Column(
        INET,
        nullable=True
    )

    destination_ip = Column(
        INET,
        nullable=True
    )

    source_port = Column(
        Integer,
        nullable=True
    )

    destination_port = Column(
        Integer,
        nullable=True
    )

    severity = Column(
        String(20),
        nullable=True
    )

    event_type = Column(
        String(100),
        nullable=True
    )

    action = Column(
        String(50),
        nullable=True
    )

    device_type = Column(
        String(50),
        nullable=True
    )

    vendor = Column(
        String(50),
        nullable=True
    )

    message = Column(
        Text,
        nullable=True
    )

    normalized_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )