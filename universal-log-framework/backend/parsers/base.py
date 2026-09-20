from abc import ABC, abstractmethod
from typing import Any


class BaseParser(ABC):
    """Common contract for built-in and filesystem drop-in parsers."""

    name: str = ""
    supported_formats: list[str] = []
    version: str = "1.0.0"

    @abstractmethod
    def detect(self, raw_sample: bytes) -> float:
        """Return a confidence score from 0.0 to 1.0."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw_event: bytes) -> tuple[list[dict[str, Any]], int, list[str]]:
        """Return events, skipped-line count, and parse errors."""
        raise NotImplementedError

    def normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Allow plugins to provide field mapping before shared normalization."""
        return parsed
