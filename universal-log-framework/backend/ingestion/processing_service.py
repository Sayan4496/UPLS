import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from dataclasses import asdict

from registry.parser_registry import detect_best_parser

from normalization.normalizer import LogNormalizer
from normalization.schema import (
    UNIVERSAL_EVENT_SCHEMA_VERSION,
    validate_universal_event,
)
from normalization.service import (
    save_duplicate_normalized_event,
    save_normalized_event,
)
from analytics.features import persist_feature_batch

from models.raw_event import RawEvent
from models.normalized_event import NormalizedEvent


class ParserOutputError(ValueError):
    def __init__(self, message, skipped_line_count=0, parse_errors=None):
        super().__init__(message)
        self.skipped_line_count = skipped_line_count
        self.parse_errors = parse_errors or []


class ProcessingService:

    PERSISTENCE_BATCH_SIZE = 500
    logger = logging.getLogger("ulpf-processing")

    @staticmethod
    def _build_status_event(
        event_hash,
        processing_timestamp,
        file_format,
        parser_used,
        parser_version,
        normalization_version,
        parser_confidence,
        status,
        duplicate_of=None,
        reason=None,
        original_event=None,
    ):
        return validate_universal_event({
            "schema_version": UNIVERSAL_EVENT_SCHEMA_VERSION,
            "event": {
                "id": event_hash,
                "timestamp": None,
                "received_at": processing_timestamp.isoformat(),
                "type": None,
                "category": None,
                "action": None,
                "severity": None,
            },
            "source": {"ip": None, "port": None, "hostname": None, "device_type": None, "vendor": None, "product": None},
            "destination": {"ip": None, "port": None, "hostname": None},
            "network": {"protocol": None, "application_protocol": None},
            "user": {"name": None, "id": None},
            "process": {"name": None, "pid": None},
            "log": {
                "source_format": file_format,
                "parser_used": parser_used,
                "parser_confidence": parser_confidence,
            },
            "message": None,
            "raw": {"original_event": original_event},
            "provenance": {
                "parser": {"name": parser_used, "version": parser_version},
                "normalizer": {"name": "LogNormalizer", "version": normalization_version},
                "detection_confidence": parser_confidence,
            },
            "processing_status": status,
            "duplicate": {"is_duplicate": status == "DUPLICATE", "duplicate_of": duplicate_of},
            "rejection": {"is_rejected": status == "REJECTED", "reason": reason},
        })

    def _build_quality_metrics(self, parsed_event, normalized_log, parser_confidence, fallback_used):

        normalized_log = normalized_log or {}

        scanned_keys = set()
        if isinstance(parsed_event, dict):
            scanned_keys = set(parsed_event.keys())

        normalized_keys = set(normalized_log.keys()) if isinstance(normalized_log, dict) else set()

        expected_fields = {
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
            "message"
        }

        missing_required_fields = [
            field for field in sorted(expected_fields)
            if normalized_log.get(field) in (None, "", [], {})
        ]

        present_count = sum(
            1 for field in expected_fields
            if normalized_log.get(field) not in (None, "", [], {})
        )

        schema_completeness = round(
            (present_count / len(expected_fields)) * 100,
            2
        ) if expected_fields else 0

        unknown_fields = len(scanned_keys - normalized_keys)

        required_fields_valid = len(missing_required_fields) == 0

        if not normalized_log:
            normalization_status = "FAILED"
        elif not required_fields_valid:
            normalization_status = "PARTIAL"
        else:
            normalization_status = "SUCCESS"

        return {
            "schema_completeness": schema_completeness,
            "required_fields_valid": required_fields_valid,
            "missing_required_fields": missing_required_fields,
            "unknown_fields": unknown_fields,
            "normalization_status": normalization_status,
            "fallback_used": fallback_used,
            "detection_confidence": parser_confidence
        }

    def process(
        self,
        db,
        upload,
        raw_content
    ):

        # --------------------------------
        # STEP 1: Detect log format
        # --------------------------------

        raw_bytes = raw_content.encode("utf-8")
        parser_match = detect_best_parser(raw_bytes)
        parser = parser_match.parser
        parser_confidence = parser_match.confidence
        file_format = parser.supported_formats[0] if parser.supported_formats else "UNKNOWN"
        fallback_used = parser.name == "FallbackParser"

        if fallback_used or parser_confidence < 0.5:
            self.logger.warning(
                "Low-confidence parser selection for filename=%s score=%s breakdown=%s",
                getattr(upload, "filename", "unknown"),
                parser_confidence,
                parser_match.score_breakdown,
            )


        # --------------------------------
        # STEP 2: Get correct parser
        # --------------------------------

        # --------------------------------
        # STEP 3: Parse raw content
        # --------------------------------

        parsed_events, skipped_line_count, parse_errors = parser.parse(raw_bytes)

        if raw_content.strip() and not parsed_events:
            reason = parse_errors[0] if parse_errors else "no events produced"
            raise ParserOutputError(
                f"Parser {parser.name} produced zero events from non-empty input: {reason}",
                skipped_line_count=skipped_line_count,
                parse_errors=parse_errors,
            )


        # --------------------------------
        # STEP 4: Create normalizer
        # --------------------------------

        normalizer = LogNormalizer()


        raw_events_created = 0

        normalized_events_created = 0

        quality_summary = {
            "records_received": len(parsed_events),
            "records_parsed": len(parsed_events),
            "records_normalized": 0,
            "duplicate_events": 0,
            "fallback_used": 0,
            "failed": 0,
            "average_confidence": 0.0,
            "parsing_success_rate": 100.0,
            "normalization_success_rate": 0.0,
            "schema_completeness": 0.0,
            "unknown_fields": 0,
            "missing_required_fields": 0,
            "detection_confidence": parser_confidence,
            "skipped_line_count": skipped_line_count,
            "parse_errors": parse_errors,
        }


        # --------------------------------
        # STEP 5: Process every event
        # --------------------------------

        parser_used = (
            "fallback_parser"
            if fallback_used
            else parser.name
        )
        parser_version = getattr(parser, "version", "1.0.0")
        normalization_version = "1.0.0"
        parser_metadata = {
            "parser_used": parser_used,
            "parser_version": parser_version,
            "normalization_version": normalization_version,
            "source_format": file_format,
            "confidence": parser_confidence,
            "fallback_used": fallback_used
        }

        events_since_commit = 0
        feature_event_ids = []

        def commit_batch():
            nonlocal events_since_commit
            persist_feature_batch(db, feature_event_ids)
            db.commit()
            events_since_commit = 0
            feature_event_ids.clear()

        for event in parsed_events:

            event_started_at = time.perf_counter()


            # --------------------------------
            # Generate checksums
            # --------------------------------

            event_payload = json.dumps(
                event,
                sort_keys=True,
                default=str
            )

            event_hash = hashlib.sha256(
                event_payload.encode(
                    "utf-8"
                )
            ).hexdigest()

            checksum = hashlib.sha256(

                raw_content.encode(
                    "utf-8"
                )

            ).hexdigest()


            # --------------------------------
            # Check for duplicate event fingerprint
            # --------------------------------

            existing_event = (
                db.query(NormalizedEvent)
                .filter(
                    NormalizedEvent.event_hash == event_hash,
                    NormalizedEvent.is_duplicate.is_(False),
                )
                .order_by(NormalizedEvent.processing_timestamp.asc(), NormalizedEvent.id.asc())
                .first()
            )

            original_raw_event = None
            if existing_event is not None:
                original_raw_event = (
                    db.query(RawEvent)
                    .filter(RawEvent.id == existing_event.raw_event_id)
                    .first()
                )

            duplicate_of = existing_event.id if existing_event else None
            is_duplicate = existing_event is not None

            # --------------------------------
            # Save Raw Event
            # --------------------------------

            raw_event = RawEvent(

                upload_id=upload.id,
                event_hash=event_hash,
                duplicate_of=(original_raw_event.id if original_raw_event else None),
                is_duplicate=is_duplicate,
                raw_log=raw_content,
                original_format=file_format,
                checksum=checksum,
                processing_status="RECEIVED"

            )


            db.add(
                raw_event
            )

            db.flush()


            raw_events_created += 1
            events_since_commit += 1

            if is_duplicate:
                quality_summary["duplicate_events"] += 1
                raw_event.processing_status = "DUPLICATE"
                raw_event.status_reason = "event_hash already exists"
                raw_event.universal_event = self._build_status_event(
                    event_hash=event_hash,
                    processing_timestamp=datetime.now(timezone.utc),
                    file_format=file_format,
                    parser_used=parser_used,
                    parser_version=parser_version,
                    normalization_version=normalization_version,
                    parser_confidence=parser_confidence,
                    status="DUPLICATE",
                    duplicate_of=str(existing_event.id) if existing_event else None,
                    reason=raw_event.status_reason,
                    original_event=event,
                )
                save_duplicate_normalized_event(
                    db=db,
                    canonical_event=existing_event,
                    raw_event_id=raw_event.id,
                    upload_id=upload.id,
                    universal_event=raw_event.universal_event,
                    processing_timestamp=datetime.now(timezone.utc),
                    status_reason=raw_event.status_reason,
                )
                if events_since_commit >= self.PERSISTENCE_BATCH_SIZE:
                    commit_batch()
                continue


            # --------------------------------
            # Normalize event
            # --------------------------------

            try:
                event = parser.normalize(event)
                normalized_data = normalizer.normalize(event)
            except Exception as error:
                raw_event.processing_status = "REJECTED"
                raw_event.status_reason = str(error)
                raw_event.universal_event = self._build_status_event(
                    event_hash=event_hash,
                    processing_timestamp=datetime.now(timezone.utc),
                    file_format=file_format,
                    parser_used=parser_used,
                    parser_version=parser_version,
                    normalization_version=normalization_version,
                    parser_confidence=parser_confidence,
                    status="REJECTED",
                    reason=raw_event.status_reason,
                    original_event=event,
                )
                quality_summary["failed"] += 1
                if events_since_commit >= self.PERSISTENCE_BATCH_SIZE:
                    commit_batch()
                continue

            normalized_log = asdict(normalized_data)

            normalized_log = json.loads(
                json.dumps(normalized_log, default=str)
            )

            processing_timestamp = datetime.now(
                timezone.utc
            )

            universal_event = {
                "schema_version": UNIVERSAL_EVENT_SCHEMA_VERSION,
                "event": {
                    "id": event_hash,
                    "timestamp": normalized_log.get("event_timestamp"),
                    "received_at": processing_timestamp.isoformat(),
                    "type": normalized_log.get("event_type"),
                    "category": event.get("category") or normalized_log.get("event_type"),
                    "action": normalized_log.get("action"),
                    "severity": normalized_log.get("severity")
                },
                "source": {
                    "ip": normalized_log.get("source_ip"),
                    "port": normalized_log.get("source_port"),
                    "hostname": (
                        event.get("hostname")
                        or event.get("host")
                        or event.get("source_hostname")
                    ),
                    "device_type": normalized_log.get("device_type"),
                    "vendor": normalized_log.get("vendor"),
                    "product": event.get("product") or event.get("source_product")
                },
                "destination": {
                    "ip": normalized_log.get("destination_ip"),
                    "port": normalized_log.get("destination_port"),
                    "hostname": (
                        event.get("destination_hostname")
                        or event.get("destination_host")
                        or event.get("dst_host")
                        or event.get("server")
                    )
                },
                "network": {
                    "protocol": event.get("protocol") or event.get("network_protocol"),
                    "application_protocol": event.get("application_protocol") or event.get("app_protocol")
                },
                "user": {
                    "name": event.get("user") or event.get("username") or event.get("user_name"),
                    "id": event.get("user_id") or event.get("uid")
                },
                "process": {
                    "name": event.get("process") or event.get("process_name"),
                    "pid": event.get("pid")
                },
                "log": {
                    "source_format": file_format,
                    "parser_used": parser_used,
                    "parser_confidence": parser_confidence
                },
                "message": normalized_log.get("message"),
                "raw": {
                    "original_event": event
                },
                "provenance": {
                    "parser": {"name": parser_used, "version": parser_version},
                    "normalizer": {"name": "LogNormalizer", "version": normalization_version},
                    "detection_confidence": parser_confidence,
                },
                "processing_status": "ACCEPTED",
                "duplicate": {"is_duplicate": False, "duplicate_of": None},
                "rejection": {"is_rejected": False, "reason": None},
            }
            validate_universal_event(universal_event)
            raw_event.processing_status = "ACCEPTED"
            raw_event.universal_event = universal_event

            quality_metrics = self._build_quality_metrics(
                parsed_event=event,
                normalized_log=normalized_log,
                parser_confidence=parser_confidence,
                fallback_used=fallback_used
            )

            processing_history = [
                {
                    "stage": "INGESTION",
                    "timestamp": processing_timestamp.isoformat(),
                    "status": "SUCCESS",
                    "upload_id": str(upload.id)
                },
                {
                    "stage": "FORMAT_DETECTION",
                    "timestamp": processing_timestamp.isoformat(),
                    "detected": file_format,
                    "confidence": parser_confidence,
                    "status": "SUCCESS"
                },
                {
                    "stage": "PARSING",
                    "timestamp": processing_timestamp.isoformat(),
                    "parser": parser_used,
                    "parser_version": parser_version,
                    "status": "SUCCESS"
                },
                {
                    "stage": "RAW_EVENT_PERSISTED",
                    "timestamp": processing_timestamp.isoformat(),
                    "raw_event_id": str(raw_event.id),
                    "checksum": checksum,
                    "status": "SUCCESS"
                },
                {
                    "stage": "NORMALIZATION",
                    "timestamp": processing_timestamp.isoformat(),
                    "schema_version": normalization_version,
                    "event_hash": event_hash,
                    "status": quality_metrics["normalization_status"],
                    "quality_metrics": quality_metrics
                }
            ]

            # --------------------------------
            # Save Normalized Event
            # --------------------------------

            normalized_event = save_normalized_event(

                db=db,

                raw_event_id=raw_event.id,
                upload_id=upload.id,
                event_hash=event_hash,
                normalized_data=normalized_data,
                normalized_log=normalized_log,
                universal_event=universal_event,
                parsed_log=event,
                parser_used=parser_used,
                parser_version=parser_version,
                normalization_version=normalization_version,
                source_format=file_format,
                parser_confidence=parser_confidence,
                fallback_used=fallback_used,
                parser_metadata=parser_metadata,
                quality_metrics=quality_metrics,
                processing_history=processing_history,
                processing_time=(
                    time.perf_counter() - event_started_at
                ),
                processing_timestamp=processing_timestamp,
                duplicate_of=duplicate_of,
                is_duplicate=is_duplicate,
                processing_status="ACCEPTED"

            )

            if normalized_event.is_duplicate:
                existing_event = db.get(
                    NormalizedEvent,
                    normalized_event.duplicate_of,
                )
                original_raw_event = (
                    db.query(RawEvent)
                    .filter(RawEvent.id == existing_event.raw_event_id)
                    .one()
                )
                raw_event.duplicate_of = original_raw_event.id
                raw_event.is_duplicate = True
                raw_event.processing_status = "DUPLICATE"
                raw_event.status_reason = "event_hash conflict during persistence"
                raw_event.universal_event = self._build_status_event(
                    event_hash=event_hash,
                    processing_timestamp=processing_timestamp,
                    file_format=file_format,
                    parser_used=parser_used,
                    parser_version=parser_version,
                    normalization_version=normalization_version,
                    parser_confidence=parser_confidence,
                    status="DUPLICATE",
                    duplicate_of=str(existing_event.id),
                    reason=raw_event.status_reason,
                    original_event=event,
                )
                normalized_event.universal_event = raw_event.universal_event
                normalized_event.status_reason = raw_event.status_reason
                quality_summary["duplicate_events"] += 1
                if events_since_commit >= self.PERSISTENCE_BATCH_SIZE:
                    db.commit()
                    events_since_commit = 0
                continue


            normalized_events_created += 1
            feature_event_ids.append(normalized_event.id)
            quality_summary["records_normalized"] += 1
            quality_summary["fallback_used"] += int(fallback_used)
            quality_summary["failed"] += int(quality_metrics["normalization_status"] != "SUCCESS")
            quality_summary["average_confidence"] += parser_confidence
            quality_summary["unknown_fields"] += quality_metrics["unknown_fields"]
            quality_summary["missing_required_fields"] += len(quality_metrics["missing_required_fields"])
            quality_summary["schema_completeness"] += quality_metrics["schema_completeness"]
            quality_summary["detection_confidence"] = max(
                quality_summary["detection_confidence"],
                parser_confidence
            )

            if events_since_commit >= self.PERSISTENCE_BATCH_SIZE:
                commit_batch()


        if events_since_commit:
            commit_batch()


        # --------------------------------
        # Return result
        # --------------------------------

        if normalized_events_created:
            quality_summary["average_confidence"] = round(
                quality_summary["average_confidence"] / normalized_events_created,
                2
            )
            quality_summary["schema_completeness"] = round(
                quality_summary["schema_completeness"] / normalized_events_created,
                2
            )

        quality_summary["parsing_success_rate"] = round(
            (quality_summary["records_parsed"] / max(quality_summary["records_received"], 1)) * 100,
            2
        )

        quality_summary["normalization_success_rate"] = round(
            ((quality_summary["records_normalized"] / max(quality_summary["records_received"], 1)) * 100),
            2
        )

        return {

            "format": file_format,

            "parsed_events": len(
                parsed_events
            ),

            "raw_events_created": raw_events_created,

            "normalized_events_created":
                normalized_events_created,

            "quality_metrics": quality_summary

        }


    # ====================================
    # BACKWARD COMPATIBILITY METHOD
    # ====================================

    def process_file(
        self,
        db,
        upload,
        raw_content
    ):

        return self.process(

            db=db,

            upload=upload,

            raw_content=raw_content

        )