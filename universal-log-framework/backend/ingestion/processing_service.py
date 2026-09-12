import hashlib
import json
import time
from datetime import datetime, timezone
from dataclasses import asdict

from detection.format_detector import FormatDetector
from registry.parser_registry import get_parser

from normalization.normalizer import LogNormalizer
from normalization.service import save_normalized_event

from models.raw_event import RawEvent


class ProcessingService:

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

        detector = FormatDetector()

        file_format = detector.detect(
            raw_content
        )


        # --------------------------------
        # STEP 2: Get correct parser
        # --------------------------------

        parser = get_parser(file_format)


        # --------------------------------
        # STEP 3: Parse raw content
        # --------------------------------

        parsed_events = parser.parse(
            raw_content
        )


        # Make sure parsed_events is a list

        if isinstance(parsed_events, dict):

            parsed_events = [
                parsed_events
            ]


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
            "fallback_used": 0,
            "failed": 0,
            "average_confidence": 0.0,
            "parsing_success_rate": 100.0,
            "normalization_success_rate": 0.0,
            "schema_completeness": 0.0,
            "unknown_fields": 0,
            "missing_required_fields": 0,
            "detection_confidence": 0.0
        }


        # --------------------------------
        # STEP 5: Process every event
        # --------------------------------

        fallback_used = file_format == "UNKNOWN"
        parser_used = (
            "fallback_parser"
            if fallback_used
            else f"{file_format.lower()}_parser"
        )
        parser_version = getattr(parser, "version", "1.0.0")
        normalization_version = "1.0.0"
        parser_confidence = 0.0 if fallback_used else 0.98

        parser_metadata = {
            "parser_used": parser_used,
            "parser_version": parser_version,
            "normalization_version": normalization_version,
            "source_format": file_format,
            "confidence": parser_confidence,
            "fallback_used": fallback_used
        }

        for event in parsed_events:

            event_started_at = time.perf_counter()


            # Convert event to string

            if isinstance(event, dict):

                event_raw_content = json.dumps(event, default=str)

            else:

                event_raw_content = str(event)


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
            # Save Raw Event
            # --------------------------------

            raw_event = RawEvent(

                upload_id=upload.id,

                raw_log=raw_content,

                original_format=file_format,

                checksum=checksum

            )


            db.add(
                raw_event
            )

            db.commit()

            db.refresh(
                raw_event
            )


            raw_events_created += 1


            # --------------------------------
            # Normalize event
            # --------------------------------

            normalized_data = normalizer.normalize(
                event
            )

            normalized_log = asdict(normalized_data)

            normalized_log = json.loads(
                json.dumps(normalized_log, default=str)
            )

            processing_timestamp = datetime.now(
                timezone.utc
            )

            universal_event = {
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
                }
            }

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

            save_normalized_event(

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
                processing_timestamp=processing_timestamp

            )


            normalized_events_created += 1
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