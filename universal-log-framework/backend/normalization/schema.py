from dataclasses import dataclass
from typing import Optional


UNIVERSAL_EVENT_SCHEMA_VERSION = "1.1.0"
PROCESSING_STATUSES = {"ACCEPTED", "DUPLICATE", "REJECTED"}


@dataclass
class NormalizedLogSchema:

    event_timestamp: Optional[str] = None

    source_ip: Optional[str] = None

    destination_ip: Optional[str] = None

    source_port: Optional[int] = None

    destination_port: Optional[int] = None

    severity: Optional[str] = None

    event_type: Optional[str] = None

    action: Optional[str] = None

    device_type: Optional[str] = None

    vendor: Optional[str] = None

    message: Optional[str] = None


def validate_universal_event(event: dict) -> dict:
    """Validate the stable event envelope before it is persisted."""
    required_sections = {"event", "source", "destination", "network", "user", "process", "log", "raw"}
    missing_sections = required_sections - set(event)
    if missing_sections:
        raise ValueError(f"Universal event is missing sections: {sorted(missing_sections)}")
    if not isinstance(event.get("schema_version"), str) or not event["schema_version"]:
        raise ValueError("Universal event schema_version must be a non-empty string")

    provenance = event.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("Universal event provenance is required")
    for key in ("parser", "normalizer", "detection_confidence"):
        if key not in provenance:
            raise ValueError(f"Universal event provenance is missing {key}")
    if not isinstance(provenance["parser"], dict) or not isinstance(provenance["normalizer"], dict):
        raise ValueError("Universal event parser and normalizer provenance must be objects")

    status = event.get("processing_status")
    if status not in PROCESSING_STATUSES:
        raise ValueError(f"Unsupported universal event processing status: {status}")
    if not isinstance(event.get("duplicate"), dict) or not isinstance(event.get("rejection"), dict):
        raise ValueError("Universal event duplicate and rejection metadata are required")
    return event