from collections import Counter
from datetime import timedelta

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import insert

from core.database import Base
from models.normalized_event import NormalizedEvent
from models.normalized_event_features import NormalizedEventFeatures


FEATURE_SCHEMA_VERSION = "1.0.0"
ROLLING_WINDOW = timedelta(hours=24)
SOURCE_TYPES = {"JSON": 1, "CSV": 2, "XML": 3, "CEF": 4, "LEEF": 5, "SYSLOG": 6, "KEYVALUE": 7}
SEVERITIES = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
ACTIONS = {"ALLOW": 1, "ACCEPT": 2, "DENY": 3, "DROP": 4, "ALERT": 5, "BLOCK": 6}


class FeatureSourceRollup(Base):
    __tablename__ = "feature_source_rollups"

    source_type = Column(String(50), primary_key=True)
    window_start = Column(DateTime(timezone=True), primary_key=True)
    event_count = Column(Integer, nullable=False)


def _code(value, mapping):
    return mapping.get((value or "").upper(), 0)


def persist_feature_batch(db, event_ids):
    """Persist features once per processing batch, not once per event.

    The batch updates hourly source rollups and reads the 24-hour totals with
    one grouped query. It never performs historical count queries per event.
    """
    if not event_ids:
        return

    events = db.query(NormalizedEvent).filter(NormalizedEvent.id.in_(event_ids)).all()
    events = [event for event in events if event.event_timestamp is not None]
    if not events:
        return

    rollup_counts = Counter()
    for event in events:
        window_start = event.event_timestamp.replace(minute=0, second=0, microsecond=0)
        rollup_counts[(event.source_format or "UNKNOWN", window_start)] += 1

    for (source_type, window_start), count in rollup_counts.items():
        statement = insert(FeatureSourceRollup).values(
            source_type=source_type,
            window_start=window_start,
            event_count=count,
        ).on_conflict_do_update(
            index_elements=[FeatureSourceRollup.source_type, FeatureSourceRollup.window_start],
            set_={"event_count": FeatureSourceRollup.event_count + count},
        )
        db.execute(statement)

    watermark = max(event.event_timestamp for event in events)
    totals = dict(
        db.query(FeatureSourceRollup.source_type, func.sum(FeatureSourceRollup.event_count))
        .filter(FeatureSourceRollup.window_start >= watermark - ROLLING_WINDOW)
        .filter(FeatureSourceRollup.window_start <= watermark)
        .group_by(FeatureSourceRollup.source_type)
        .all()
    )

    feature_rows = []
    for event in events:
        event_time = event.event_timestamp
        source_type = event.source_format or "UNKNOWN"
        feature_rows.append({
            "event_id": event.id,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "source_type": source_type,
            "source_type_code": _code(source_type, SOURCE_TYPES),
            "severity_code": _code(event.severity, SEVERITIES),
            "action_code": _code(event.action, ACTIONS),
            "event_hour": event_time.hour,
            "event_day_of_week": event_time.weekday(),
            "source_event_count_24h": int(totals.get(source_type, 0) or 0),
        })

    excluded = insert(NormalizedEventFeatures).excluded
    db.execute(insert(NormalizedEventFeatures).values(feature_rows).on_conflict_do_update(
        index_elements=[NormalizedEventFeatures.event_id],
        set_={column: getattr(excluded, column) for column in (
            "feature_schema_version", "source_type", "source_type_code", "severity_code",
            "action_code", "event_hour", "event_day_of_week", "source_event_count_24h",
        )},
    ))