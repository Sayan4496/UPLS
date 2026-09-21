import csv
import io
import json
from datetime import datetime, timedelta
from typing import Iterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import String, or_
from sqlalchemy.orm import Session

from core.config import EXPORT_FETCH_BATCH_SIZE, MAX_EXPORT_RECORDS
from core.database import SessionLocal
from models.normalized_event import NormalizedEvent
from models.normalized_event_features import NormalizedEventFeatures
from models.raw_event import RawEvent
from datalake.exporter import DataLakeExporter


router = APIRouter(
    prefix="/api/v1/export",
    tags=["Export"]
)


@router.get("/datalake/status")
def datalake_status():
    return DataLakeExporter.read_status()


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
        "schema_version": "1.1.0",
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
        },
        "provenance": {
            "parser": {"name": event.parser_used, "version": event.parser_version},
            "normalizer": {"name": "LogNormalizer", "version": event.normalization_version},
            "detection_confidence": event.parser_confidence,
        },
        "processing_status": event.processing_status,
        "duplicate": {"is_duplicate": bool(event.is_duplicate), "duplicate_of": str(event.duplicate_of) if event.duplicate_of else None},
        "rejection": {"is_rejected": event.processing_status == "REJECTED", "reason": event.status_reason},
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
        "duplicate_of": str(event.duplicate_of) if event.duplicate_of else None,
        "is_duplicate": bool(event.is_duplicate),
        "processing_status": event.processing_status,
        "status_reason": event.status_reason,
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
    query = db.query(NormalizedEvent, RawEvent).outerjoin(
        RawEvent,
        RawEvent.id == NormalizedEvent.raw_event_id,
    )

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

    return query.order_by(
        NormalizedEvent.event_timestamp.desc().nulls_last(),
        NormalizedEvent.normalized_at.desc(),
        NormalizedEvent.id.desc(),
    )


def _iter_export_records(db: Session, **filters) -> Iterator[dict]:
    query = _get_export_query(db=db, **filters).limit(MAX_EXPORT_RECORDS)
    for event, raw_event in query.execution_options(stream_results=True).yield_per(EXPORT_FETCH_BATCH_SIZE):
        yield _build_export_record(event, raw_event)


def _stream_json(records: Iterator[dict]):
    yield "["
    first = True
    for record in records:
        if not first:
            yield ","
        yield json.dumps(record, default=str)
        first = False
    yield "]"


EXPORT_FIELDS = [
    "id", "raw_event_id", "upload_id", "event_hash", "duplicate_of", "is_duplicate",
    "processing_status", "status_reason", "event_timestamp", "source_ip", "destination_ip",
    "source_port", "destination_port", "severity", "event_type", "action", "device_type",
    "vendor", "message", "parser_used", "source_format", "parser_confidence", "fallback_used",
    "processing_timestamp", "universal_event",
]


def _csv_row(record):
    return {
        "id": record["id"], "raw_event_id": record["raw_event_id"], "upload_id": record["upload_id"],
        "event_hash": record["event_hash"], "duplicate_of": record.get("duplicate_of"),
        "is_duplicate": record.get("is_duplicate"), "processing_status": record.get("processing_status"),
        "status_reason": record.get("status_reason"), "event_timestamp": record["event"]["event_timestamp"],
        "source_ip": record["event"]["source_ip"], "destination_ip": record["event"]["destination_ip"],
        "source_port": record["event"]["source_port"], "destination_port": record["event"]["destination_port"],
        "severity": record["event"]["severity"], "event_type": record["event"]["event_type"],
        "action": record["event"]["action"], "device_type": record["event"]["device_type"],
        "vendor": record["event"]["vendor"], "message": record["event"]["message"],
        "parser_used": record["parser_information"]["parser_used"],
        "source_format": record["parser_information"]["source_format"],
        "parser_confidence": record["parser_information"]["parser_confidence"],
        "fallback_used": record["parser_information"]["fallback_used"],
        "processing_timestamp": record["parser_information"]["processing_timestamp"],
        "universal_event": json.dumps(record["universal_event"], default=str),
    }


def _stream_csv(records: Iterator[dict]):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    yield buffer.getvalue()
    for record in records:
        buffer.seek(0)
        buffer.truncate(0)
        writer.writerow(_csv_row(record))
        yield buffer.getvalue()


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
    return StreamingResponse(
        _stream_json(_iter_export_records(
            db, severity=severity, source_format=source_format, event_type=event_type,
            search=search, host=host, parser=parser, date_from=date_from, date_to=date_to,
        )),
        media_type="application/json",
    )


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
    return StreamingResponse(
        _stream_csv(_iter_export_records(
            db, severity=severity, source_format=source_format, event_type=event_type,
            search=search, host=host, parser=parser, date_from=date_from, date_to=date_to,
        )),
        media_type="text/csv; charset=utf-8",
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
    def rows():
        for record in _iter_export_records(
            db, severity=severity, source_format=source_format, event_type=event_type,
            search=search, host=host, parser=parser, date_from=date_from, date_to=date_to,
        ):
            yield json.dumps(record, default=str) + "\n"

    return StreamingResponse(
        rows(),
        media_type="application/x-ndjson; charset=utf-8",
    )


@router.get("/ml-dataset")
def export_ml_dataset(db: Session = Depends(get_db)):
    def rows():
        query = (
            db.query(NormalizedEventFeatures)
            .join(NormalizedEvent, NormalizedEvent.id == NormalizedEventFeatures.event_id)
            .order_by(NormalizedEvent.event_timestamp.desc(), NormalizedEvent.id.desc())
            .limit(MAX_EXPORT_RECORDS)
        )
        for feature in query.execution_options(stream_results=True).yield_per(EXPORT_FETCH_BATCH_SIZE):
            yield json.dumps({
                "event_id": str(feature.event_id),
                "feature_schema_version": feature.feature_schema_version,
                "source_type": feature.source_type,
                "source_type_code": feature.source_type_code,
                "severity_code": feature.severity_code,
                "action_code": feature.action_code,
                "event_hour": feature.event_hour,
                "event_day_of_week": feature.event_day_of_week,
                "source_event_count_24h": feature.source_event_count_24h,
            }) + "\n"

    return StreamingResponse(rows(), media_type="application/x-ndjson; charset=utf-8")
