import csv
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import String, or_
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.normalized_event import NormalizedEvent
from models.raw_event import RawEvent


router = APIRouter(
    prefix="/api/v1/export",
    tags=["Export"]
)


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def _build_universal_event(event):
    if event.universal_event:
        return event.universal_event

    return {
        "event": {
            "id": event.event_hash,
            "timestamp": _serialize_value(event.event_timestamp),
            "received_at": _serialize_value(event.processing_timestamp),
            "type": event.event_type,
            "category": event.event_type,
            "action": event.action,
            "severity": event.severity
        },
        "source": {
            "ip": _serialize_value(event.source_ip),
            "port": event.source_port,
            "hostname": None,
            "device_type": event.device_type,
            "vendor": event.vendor,
            "product": None
        },
        "destination": {
            "ip": _serialize_value(event.destination_ip),
            "port": event.destination_port,
            "hostname": None
        },
        "network": {
            "protocol": None,
            "application_protocol": None
        },
        "user": {
            "name": None,
            "id": None
        },
        "process": {
            "name": None,
            "pid": None
        },
        "log": {
            "source_format": event.source_format,
            "parser_used": event.parser_used,
            "parser_confidence": event.parser_confidence
        },
        "message": event.message,
        "raw": {
            "original_event": event.parsed_log
        }
    }


def _build_export_record(event, raw_event):
    parser_information = {
        **(event.parser_metadata or {}),
        "parser_used": event.parser_used,
        "parser_version": event.parser_version,
        "normalization_version": event.normalization_version,
        "processing_time": event.processing_time,
        "processing_timestamp": _serialize_value(event.processing_timestamp),
        "source_format": event.source_format,
        "parser_confidence": event.parser_confidence,
        "fallback_used": event.fallback_used
    }

    return {
        "id": str(event.id),
        "raw_event_id": str(event.raw_event_id),
        "upload_id": str(event.upload_id),
        "event_hash": event.event_hash,
        "raw_log": raw_event.raw_content if raw_event else None,
        "parsed_data": event.parsed_log,
        "normalized_data": event.normalized_log,
        "universal_event": _build_universal_event(event),
        "quality_metrics": event.quality_metrics or {},
        "processing_history": event.processing_history or [],
        "parser_information": parser_information,
        "event": {
            "event_timestamp": _serialize_value(event.event_timestamp),
            "source_ip": _serialize_value(event.source_ip),
            "destination_ip": _serialize_value(event.destination_ip),
            "source_port": event.source_port,
            "destination_port": event.destination_port,
            "severity": event.severity,
            "event_type": event.event_type,
            "action": event.action,
            "device_type": event.device_type,
            "vendor": event.vendor,
            "message": event.message
        }
    }


def _get_export_query(
    db: Session,
    severity: str | None = None,
    source_format: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
    host: str | None = None,
    parser: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None
):
    query = db.query(NormalizedEvent)

    if severity:
        query = query.filter(NormalizedEvent.severity == severity)

    if source_format:
        query = query.filter(NormalizedEvent.source_format.ilike(source_format))

    if event_type:
        query = query.filter(NormalizedEvent.event_type == event_type)

    if parser:
        query = query.filter(NormalizedEvent.parser_used.ilike(parser))

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
        query = query.filter(NormalizedEvent.event_timestamp >= date_from)

    if date_to:
        inclusive_date_to = date_to

        if len(date_to) == 10:
            inclusive_date_to = datetime.fromisoformat(date_to) + timedelta(days=1)

        query = query.filter(NormalizedEvent.event_timestamp < inclusive_date_to)

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

    return (
        query
        .order_by(
            NormalizedEvent.event_timestamp.desc().nulls_last(),
            NormalizedEvent.normalized_at.desc(),
            NormalizedEvent.id.desc()
        )
        .all()
    )


def _load_export_records(
    db: Session,
    severity: str | None = None,
    source_format: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
    host: str | None = None,
    parser: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    events = _get_export_query(
        db=db,
        severity=severity,
        source_format=source_format,
        event_type=event_type,
        search=search,
        host=host,
        parser=parser,
        date_from=date_from,
        date_to=date_to
    )

    raw_events = (
        db.query(RawEvent)
        .filter(RawEvent.id.in_([event.raw_event_id for event in events]))
        .all()
    )

    raw_lookup = {raw_event.id: raw_event for raw_event in raw_events}

    return [
        _build_export_record(event, raw_lookup.get(event.raw_event_id))
        for event in events
    ]


@router.get("/json")
def export_json(
    severity: str | None = Query(default=None),
    source_format: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    host: str | None = Query(default=None),
    parser: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    records = _load_export_records(
        db=db,
        severity=severity,
        source_format=source_format,
        event_type=event_type,
        search=search,
        host=host,
        parser=parser,
        date_from=date_from,
        date_to=date_to
    )

    return JSONResponse(content=records)


@router.get("/csv")
def export_csv(
    severity: str | None = Query(default=None),
    source_format: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    host: str | None = Query(default=None),
    parser: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    records = _load_export_records(
        db=db,
        severity=severity,
        source_format=source_format,
        event_type=event_type,
        search=search,
        host=host,
        parser=parser,
        date_from=date_from,
        date_to=date_to
    )

    fieldnames = [
        "id",
        "raw_event_id",
        "upload_id",
        "event_hash",
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
        "parser_used",
        "source_format",
        "parser_confidence",
        "fallback_used",
        "processing_timestamp",
        "universal_event"
    ]

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()

    for record in records:
        row = {
            "id": record["id"],
            "raw_event_id": record["raw_event_id"],
            "upload_id": record["upload_id"],
            "event_hash": record["event_hash"],
            "event_timestamp": record["event"]["event_timestamp"],
            "source_ip": record["event"]["source_ip"],
            "destination_ip": record["event"]["destination_ip"],
            "source_port": record["event"]["source_port"],
            "destination_port": record["event"]["destination_port"],
            "severity": record["event"]["severity"],
            "event_type": record["event"]["event_type"],
            "action": record["event"]["action"],
            "device_type": record["event"]["device_type"],
            "vendor": record["event"]["vendor"],
            "message": record["event"]["message"],
            "parser_used": record["parser_information"]["parser_used"],
            "source_format": record["parser_information"]["source_format"],
            "parser_confidence": record["parser_information"]["parser_confidence"],
            "fallback_used": record["parser_information"]["fallback_used"],
            "processing_timestamp": record["parser_information"]["processing_timestamp"],
            "universal_event": json.dumps(record["universal_event"], default=str)
        }

        writer.writerow(row)

    return PlainTextResponse(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8"
    )


@router.get("/ndjson")
def export_ndjson(
    severity: str | None = Query(default=None),
    source_format: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    host: str | None = Query(default=None),
    parser: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: Session = Depends(get_db)
):
    records = _load_export_records(
        db=db,
        severity=severity,
        source_format=source_format,
        event_type=event_type,
        search=search,
        host=host,
        parser=parser,
        date_from=date_from,
        date_to=date_to
    )

    payload = "\n".join(
        json.dumps(record, default=str)
        for record in records
    )

    if payload:
        payload += "\n"

    return PlainTextResponse(
        payload,
        media_type="application/x-ndjson; charset=utf-8"
    )
