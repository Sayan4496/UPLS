from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta

from sqlalchemy import String, or_
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.normalized_event import NormalizedEvent
from models.raw_event import RawEvent


router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# GET ALL EVENTS
@router.get("/")
def get_events(

    severity: str = Query(None),
    source_ip: str = Query(None),
    destination_ip: str = Query(None),
    event_type: str = Query(None),
    search: str = Query(None),
    source_format: str = Query(None),
    host: str = Query(None),
    parser: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),

    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),

    db: Session = Depends(get_db)
):

    query = db.query(NormalizedEvent)


    # Filters

    if severity:

        query = query.filter(
            NormalizedEvent.severity == severity
        )


    if source_ip:

        query = query.filter(
            NormalizedEvent.source_ip == source_ip
        )


    if destination_ip:

        query = query.filter(
            NormalizedEvent.destination_ip == destination_ip
        )


    if event_type:

        query = query.filter(
            NormalizedEvent.event_type == event_type
        )


    if source_format:

        query = query.filter(
            NormalizedEvent.source_format.ilike(source_format)
        )


    if parser:

        query = query.filter(
            NormalizedEvent.parser_used.ilike(parser)
        )


    if host:

        query = query.filter(
            or_(
                NormalizedEvent.device_type.ilike(f"%{host}%"),
                NormalizedEvent.vendor.ilike(f"%{host}%"),
                NormalizedEvent.parsed_log["host"].astext.ilike(f"%{host}%"),
                NormalizedEvent.parsed_log["hostname"].astext.ilike(f"%{host}%")
            )
        )


    if date_from:

        query = query.filter(
            NormalizedEvent.event_timestamp >= date_from
        )


    if date_to:

        inclusive_date_to = date_to

        if len(date_to) == 10:
            inclusive_date_to = datetime.fromisoformat(date_to) + timedelta(days=1)

        query = query.filter(
            NormalizedEvent.event_timestamp < inclusive_date_to
        )
        
        
    # Search in log message
    if search:

        search_value = f"%{search}%"
        query = query.filter(
            or_(
                NormalizedEvent.message.ilike(search_value),
                NormalizedEvent.event_type.ilike(search_value),
                NormalizedEvent.source_ip.cast(String).ilike(search_value),
                NormalizedEvent.destination_ip.cast(String).ilike(search_value),
                NormalizedEvent.action.ilike(search_value),
                NormalizedEvent.parsed_log.cast(String).ilike(search_value)
            )
        )


    # Total records

    total_events = query.count()


    # Pagination calculation

    offset = (page - 1) * limit


    # Fetch paginated events

    events = (
        query
        .order_by(
            NormalizedEvent.event_timestamp.desc().nulls_last(),
            NormalizedEvent.normalized_at.desc(),
            NormalizedEvent.id.desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


    return {

        "total_events": total_events,

        "page": page,

        "limit": limit,

        "total_pages": (
            (total_events + limit - 1) // limit
        ),

        "events": events
    }

# GET EVENT STATISTICS
# IMPORTANT: This must come BEFORE /{event_id}
@router.get("/stats")
def get_event_stats(
    db: Session = Depends(get_db)
):

    total_events = db.query(NormalizedEvent).count()

    high_severity = (
        db.query(NormalizedEvent)
        .filter(NormalizedEvent.severity == "HIGH")
        .count()
    )

    medium_severity = (
        db.query(NormalizedEvent)
        .filter(NormalizedEvent.severity == "MEDIUM")
        .count()
    )

    low_severity = (
        db.query(NormalizedEvent)
        .filter(NormalizedEvent.severity == "LOW")
        .count()
    )

    return {
        "total_events": total_events,
        "high_severity": high_severity,
        "medium_severity": medium_severity,
        "low_severity": low_severity
    }


# GET SINGLE EVENT
@router.get("/{event_id}")
def get_event(

    event_id: str,

    db: Session = Depends(get_db)
):

    event = (
        db.query(NormalizedEvent)
        .filter(
            NormalizedEvent.id == event_id
        )
        .first()
    )


    if not event:

        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )


    raw_event = (
        db.query(RawEvent)
        .filter(RawEvent.id == event.raw_event_id)
        .first()
    )

    return {
        "id": str(event.id),
        "raw_event_id": str(event.raw_event_id),
        "upload_id": str(event.upload_id),
        "event_hash": event.event_hash,
        "duplicate_of": str(event.duplicate_of) if event.duplicate_of else None,
        "is_duplicate": bool(event.is_duplicate),
        "raw_log": raw_event.raw_log if raw_event else None,
        "parsed_data": event.parsed_log,
        "normalized_data": event.normalized_log,
        "universal_event": event.universal_event or {},
        "quality_metrics": event.quality_metrics or {
            "schema_completeness": 0,
            "required_fields_valid": False,
            "normalization_status": "UNKNOWN"
        },
        "processing_history": event.processing_history or [],
        "parser_information": {
            **event.parser_metadata,
            "parser_used": event.parser_used,
            "parser_version": event.parser_version,
            "normalization_version": event.normalization_version,
            "processing_time": event.processing_time,
            "processing_timestamp": event.processing_timestamp
        },
        "event": {
            "event_timestamp": event.event_timestamp,
            "source_ip": event.source_ip,
            "destination_ip": event.destination_ip,
            "severity": event.severity,
            "event_type": event.event_type,
            "message": event.message
        }
    }
