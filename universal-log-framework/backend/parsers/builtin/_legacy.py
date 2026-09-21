import json
import re
from typing import Any

from parsers.base import BaseParser


class LegacyParserAdapter(BaseParser):
    legacy_parser_class = None
    name = ""
    supported_formats: list[str] = []
    detect_score = 0.0

    def _legacy_parser(self):
        return self.legacy_parser_class()

    def detect(self, raw_sample: bytes) -> float:
        text = raw_sample.decode("utf-8", errors="replace").strip()
        if not text:
            return 0.0
        format_name = self.supported_formats[0]
        if format_name == "JSON":
            try:
                json.loads(text)
                return self.detect_score
            except json.JSONDecodeError:
                lines = [line for line in text.splitlines() if line.strip()]
                if len(lines) > 1 and all(self._is_json_line(line) for line in lines):
                    return 0.91
                return 0.0
        if format_name == "XML":
            return self.detect_score if text.startswith("<") and text.endswith(">") else 0.0
        if format_name in {"CEF", "LEEF"}:
            return self.detect_score if text.splitlines()[0].startswith(f"{format_name}:") else 0.0
        if format_name == "SYSLOG":
            pattern = r"^(?:<\d+>)?[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s+"
            return self.detect_score if re.match(pattern, text.splitlines()[0]) else 0.0
        if format_name == "KEYVALUE":
            first_line = text.splitlines()[0]
            return self.detect_score if "=" in first_line and re.search(r"\w+\s*=", first_line) else 0.0
        if format_name == "CSV":
            lines = [line for line in text.splitlines() if line.strip()]
            return self.detect_score if len(lines) >= 2 and "," in lines[0] else 0.0
        return 0.0

    @staticmethod
    def _is_json_line(line: str) -> bool:
        try:
            return isinstance(json.loads(line), dict)
        except json.JSONDecodeError:
            return False

    def parse(self, raw_event: bytes) -> tuple[list[dict[str, Any]], int, list[str]]:
        text = raw_event.decode("utf-8")
        parser = self._legacy_parser()
        try:
            events = parser.parse(text)
        except Exception as error:
            return [], 0, [str(error)]

        if isinstance(events, dict):
            events = [events]
        return events, 0, []

    def normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        return parsed


class LineAwareLegacyAdapter(LegacyParserAdapter):
    """Adds explicit skipped-line accounting to legacy line parsers."""

    def parse(self, raw_event: bytes) -> tuple[list[dict[str, Any]], int, list[str]]:
        text = raw_event.decode("utf-8")
        parser = self._legacy_parser()
        try:
            events = parser.parse(text)
        except Exception as error:
            return [], 0, [str(error)]

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        skipped_line_count = getattr(parser, "skipped_line_count", 0)
        parse_errors = getattr(parser, "parse_errors", [])
        if self.name in {"CEFParser", "LEEFParser"}:
            candidate_lines = [
                line for line in lines
                if line.startswith(f"{self.supported_formats[0]}:")
            ]
            skipped_line_count = max(len(candidate_lines) - len(events), 0)
            skipped_line_count += sum(
                1 for line in lines
                if not line.startswith("#") and not line.startswith(f"{self.supported_formats[0]}:")
            )
        elif self.name == "KeyValueParser":
            data_lines = [line for line in lines if not line.startswith("#")]
            skipped_line_count = max(
                skipped_line_count,
                len(data_lines) - len(events),
            )

        return events, skipped_line_count, parse_errors
