from copy import deepcopy

from models.normalized_event import NormalizedEvent
from sqlalchemy.exc import IntegrityError


def _duplicate_universal_event(universal_event, canonical_id):
    duplicate_event = deepcopy(universal_event)
    duplicate_event["processing_status"] = "DUPLICATE"
    duplicate_event["duplicate"] = {
        "is_duplicate": True,
        "duplicate_of": str(canonical_id),
    }
    return duplicate_event


def save_normalized_event(
    db,
    raw_event_id,
    upload_id,
    event_hash,
    normalized_data,
    normalized_log,
    universal_event,
    parsed_log,
    parser_used,
    parser_version,
    normalization_version,
    source_format,
    parser_confidence,
    fallback_used,
    parser_metadata,
    quality_metrics,
    processing_history,
    processing_time,
    processing_timestamp,
    duplicate_of=None,
    is_duplicate=False,
    processing_status="ACCEPTED",
    status_reason=None
):

    values = dict(
        raw_event_id=raw_event_id,
        upload_id=upload_id,
        event_hash=event_hash,
        duplicate_of=duplicate_of,
        is_duplicate=is_duplicate,
        processing_status=processing_status,
        status_reason=status_reason,
        parsed_log=parsed_log,
        normalized_log=normalized_log,
        universal_event=universal_event,
        parser_used=parser_used,
        parser_version=parser_version,
        normalization_version=normalization_version,
        source_format=source_format,
        parser_confidence=parser_confidence,
        fallback_used=fallback_used,
        parser_metadata=parser_metadata,
        quality_metrics=quality_metrics,
        processing_history=processing_history,
        processing_time=processing_time,
        processing_timestamp=processing_timestamp,
        event_timestamp=normalized_data.event_timestamp,
        source_ip=normalized_data.source_ip,
        destination_ip=normalized_data.destination_ip,
        source_port=normalized_data.source_port,
        destination_port=normalized_data.destination_port,
        severity=normalized_data.severity,
        event_type=normalized_data.event_type,
        action=normalized_data.action,
        device_type=normalized_data.device_type,
        vendor=normalized_data.vendor,
        message=normalized_data.message
    )

    normalized_event = NormalizedEvent(**values)
    try:
        with db.begin_nested():
            db.add(normalized_event)
            db.flush()
        return normalized_event
    except IntegrityError:
        canonical_event = (
            db.query(NormalizedEvent)
            .filter(
                NormalizedEvent.event_hash == event_hash,
                NormalizedEvent.is_duplicate.is_(False),
            )
            .order_by(
                NormalizedEvent.processing_timestamp.asc(),
                NormalizedEvent.id.asc(),
            )
            .first()
        )
        if canonical_event is None:
            raise

        values.update(
            duplicate_of=canonical_event.id,
            is_duplicate=True,
            processing_status="DUPLICATE",
            status_reason="event_hash conflict during persistence",
            universal_event=_duplicate_universal_event(
                universal_event,
                canonical_event.id,
            ),
        )
        duplicate_event = NormalizedEvent(**values)
        db.add(duplicate_event)
        db.flush()
        return duplicate_event


def save_duplicate_normalized_event(
    db,
    canonical_event,
    raw_event_id,
    upload_id,
    universal_event,
    processing_timestamp,
    status_reason,
):
    clone_fields = (
        "parsed_log",
        "normalized_log",
        "parser_used",
        "parser_version",
        "normalization_version",
        "source_format",
        "parser_confidence",
        "fallback_used",
        "parser_metadata",
        "quality_metrics",
        "processing_history",
        "processing_time",
        "event_timestamp",
        "source_ip",
        "destination_ip",
        "source_port",
        "destination_port",
        "severity",
        "event_type",
        "action",
        "device_type",
        "vendor",
        "message",
    )
    values = {
        field: getattr(canonical_event, field)
        for field in clone_fields
    }
    duplicate_event = NormalizedEvent(
        **values,
        raw_event_id=raw_event_id,
        upload_id=upload_id,
        event_hash=canonical_event.event_hash,
        duplicate_of=canonical_event.id,
        is_duplicate=True,
        processing_status="DUPLICATE",
        status_reason=status_reason,
        universal_event=universal_event,
        processing_timestamp=processing_timestamp,
    )
    db.add(duplicate_event)
    db.flush()
    return duplicate_event