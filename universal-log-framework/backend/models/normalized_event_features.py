from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.database import Base


class NormalizedEventFeatures(Base):
    __tablename__ = "normalized_event_features"

    event_id = Column(UUID(as_uuid=True), ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True)
    feature_schema_version = Column(String(20), nullable=False, default="1.0.0")
    source_type = Column(String(50), nullable=False)
    source_type_code = Column(Integer, nullable=False)
    severity_code = Column(Integer, nullable=False)
    action_code = Column(Integer, nullable=False)
    event_hour = Column(Integer, nullable=False)
    event_day_of_week = Column(Integer, nullable=False)
    source_event_count_24h = Column(Integer, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)