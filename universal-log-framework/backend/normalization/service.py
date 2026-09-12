from models.normalized_event import NormalizedEvent


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
    is_duplicate=False
):

    normalized_event = NormalizedEvent(

        raw_event_id=raw_event_id,

        upload_id=upload_id,

        event_hash=event_hash,

        duplicate_of=duplicate_of,

        is_duplicate=is_duplicate,

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

    db.add(normalized_event)

    db.commit()

    db.refresh(normalized_event)

    return normalized_event