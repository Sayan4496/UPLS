import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID, INET
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