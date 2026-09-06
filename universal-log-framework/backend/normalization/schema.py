from dataclasses import dataclass
from typing import Optional


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