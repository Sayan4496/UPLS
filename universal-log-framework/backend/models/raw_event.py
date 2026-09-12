import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import synonym
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class RawEvent(Base):

    __tablename__ = "raw_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("uploads.id"),
        nullable=False
    )

    event_hash = Column(
        String(64),
        nullable=True,
        index=True
    )

    duplicate_of = Column(
        UUID(as_uuid=True),
        ForeignKey("raw_events.id", ondelete="SET NULL"),
        nullable=True
    )

    is_duplicate = Column(
        Boolean,
        nullable=False,
        default=False
    )

    raw_log = Column(
        "raw_content",
        Text,
        nullable=False
    )

    raw_content = synonym("raw_log")

    original_format = Column(
        String(20),
        nullable=False
    )

    checksum = Column(
        String(64),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )