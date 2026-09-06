from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.normalized_event import NormalizedEvent


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

    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    
    sort_by: str = Query("event_timestamp"),
    order: str = Query("desc"),

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
        
        
    # Search in log message
    if search:

        query = query.filter(
            NormalizedEvent.message.ilike(
                f"%{search}%"
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
            NormalizedEvent.normalized_at.desc(),
            NormalizedEvent.event_timestamp.desc(),
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


    return event

    # Allowed sorting fields
    allowed_sort_fields = [
        "event_timestamp",
        "severity",
        "source_ip",
        "destination_ip",
        "event_type"
    ]


    if sort_by not in allowed_sort_fields:

        raise HTTPException(
            status_code=400,
            detail="Invalid sort field"
        )


    sort_column = getattr(
        NormalizedEvent,
        sort_by
    )


    if order.lower() == "asc":

        query = query.order_by(
            sort_column.asc()
        )

    elif order.lower() == "desc":

        query = query.order_by(
            sort_column.desc()
        )

    else:

        raise HTTPException(
            status_code=400,
            detail="Order must be asc or desc"
        )