import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
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

    raw_content = Column(
        Text,
        nullable=False
    )

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