from models.normalized_event import NormalizedEvent


def save_normalized_event(
    db,
    raw_event_id,
    normalized_data
):

    normalized_event = NormalizedEvent(

        raw_event_id=raw_event_id,

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