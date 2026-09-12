from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.normalized_event import NormalizedEvent


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)


def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/parser-coverage")
def get_parser_coverage(db: Session = Depends(get_db)):

    total_events = db.query(NormalizedEvent).count()

    rows = (
        db.query(
            func.coalesce(
                NormalizedEvent.parser_used,
                "unknown_parser"
            ).label("parser_used"),
            func.coalesce(
                NormalizedEvent.source_format,
                "UNKNOWN"
            ).label("source_format"),
            func.coalesce(
                NormalizedEvent.fallback_used,
                False
            ).label("fallback_used"),
            func.count(NormalizedEvent.id).label("count")
        )
        .group_by(
            func.coalesce(NormalizedEvent.parser_used, "unknown_parser"),
            func.coalesce(NormalizedEvent.source_format, "UNKNOWN"),
            func.coalesce(NormalizedEvent.fallback_used, False)
        )
        .order_by(func.count(NormalizedEvent.id).desc())
        .all()
    )

    return {
        "total_events": total_events,
        "coverage": [
            {
                "parser_used": row.parser_used,
                "source_format": row.source_format,
                "fallback_used": row.fallback_used,
                "count": row.count,
                "percentage": round(
                    (row.count / total_events) * 100,
                    2
                ) if total_events else 0
            }
            for row in rows
        ]
    }


@router.get("/dashboard")
def get_analytics_dashboard(db: Session = Depends(get_db)):

    total_logs = db.query(NormalizedEvent).count()
    alerts = (
        db.query(NormalizedEvent)
        .filter(NormalizedEvent.severity.in_(
            ["HIGH", "CRITICAL", "ERROR"]
        ))
        .count()
    )

    source_types = db.query(
        func.count(func.distinct(func.coalesce(
            NormalizedEvent.source_format,
            "UNKNOWN"
        )))
    ).scalar() or 0

    unique_hosts = db.query(
        func.count(func.distinct(NormalizedEvent.source_ip))
    ).scalar() or 0

    user_values = func.coalesce(
        NormalizedEvent.parsed_log["username"].astext,
        NormalizedEvent.parsed_log["user"].astext,
        NormalizedEvent.parsed_log["user_name"].astext
    )
    unique_users = db.query(
        func.count(func.distinct(user_values))
    ).filter(user_values.isnot(None)).scalar() or 0

    date_bounds = db.query(
        func.min(NormalizedEvent.event_timestamp),
        func.max(NormalizedEvent.event_timestamp)
    ).first()

    volume_rows = db.query(
        func.date(NormalizedEvent.event_timestamp).label("date"),
        func.count(NormalizedEvent.id).label("logs"),
        func.sum(case(
            (NormalizedEvent.severity.in_(["HIGH", "CRITICAL", "ERROR"]), 1),
            else_=0
        )).label("errors")
    ).filter(
        NormalizedEvent.event_timestamp.isnot(None)
    ).group_by(
        func.date(NormalizedEvent.event_timestamp)
    ).order_by(
        func.date(NormalizedEvent.event_timestamp)
    ).all()

    severity_rows = db.query(
        NormalizedEvent.severity,
        func.count(NormalizedEvent.id).label("count")
    ).group_by(NormalizedEvent.severity).order_by(
        func.count(NormalizedEvent.id).desc()
    ).all()

    health_rows = db.query(
        func.coalesce(
            NormalizedEvent.device_type,
            NormalizedEvent.vendor,
            "Unknown source"
        ).label("source"),
        func.count(NormalizedEvent.id).label("logs"),
        func.sum(case(
            (NormalizedEvent.severity.in_(["HIGH", "CRITICAL", "ERROR"]), 1),
            else_=0
        )).label("errors")
    ).group_by(
        func.coalesce(
            NormalizedEvent.device_type,
            NormalizedEvent.vendor,
            "Unknown source"
        )
    ).order_by(func.count(NormalizedEvent.id).desc()).limit(8).all()

    def iso_date(value):
        return value.isoformat() if value else None

    def source_status(error_count, log_count):
        rate = error_count / log_count if log_count else 0
        if rate >= 0.5:
            return "Error"
        if rate >= 0.2:
            return "Warning"
        return "Healthy"

    return {
        "summary": {
            "total_logs": total_logs,
            "alerts": alerts,
            "source_types": source_types,
            "unique_hosts": unique_hosts,
            "unique_users": unique_users,
            "date_start": iso_date(date_bounds[0]),
            "date_end": iso_date(date_bounds[1])
        },
        "volume": [
            {
                "date": row.date.isoformat(),
                "logs": row.logs,
                "errors": row.errors or 0,
                "error_rate": round(
                    ((row.errors or 0) / row.logs) * 100,
                    2
                ) if row.logs else 0
            }
            for row in volume_rows
        ],
        "severity": [
            {"label": row.severity or "UNKNOWN", "count": row.count}
            for row in severity_rows
        ],
        "source_health": [
            {
                "source": row.source,
                "logs": row.logs,
                "status": source_status(row.errors or 0, row.logs)
            }
            for row in health_rows
        ]
    }