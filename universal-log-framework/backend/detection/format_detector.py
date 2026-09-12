import json
import re

from detection.confidence_engine import ConfidenceEngine
from detection.detector_registry import DetectorRegistry


class FormatDetector:

    @staticmethod
    def _json_detector(raw_content):
        raw_content = raw_content.strip()

        if not raw_content:
            return {"score": 0.0, "reason": "Empty input"}

        try:
            json.loads(raw_content)
            return {
                "score": 0.96,
                "reason": "Valid JSON document detected"
            }
        except json.JSONDecodeError:
            pass

        lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
        json_lines = 0

        for line in lines:
            try:
                json.loads(line)
                json_lines += 1
            except json.JSONDecodeError:
                continue

        if json_lines and json_lines == len(lines) and len(lines) > 1:
            return {
                "score": 0.91,
                "reason": "JSON lines detected"
            }

        return {
            "score": 0.0,
            "reason": "Not valid JSON"
        }

    @staticmethod
    def _xml_detector(raw_content):
        first_content_line = ""

        for line in raw_content.splitlines():
            line = line.strip()

            if line and not line.startswith("#"):
                first_content_line = line
                break

        if (
            first_content_line.startswith("<")
            and first_content_line.endswith(">")
        ):
            return {
                "score": 0.83,
                "reason": "XML-like document structure detected"
            }

        return {"score": 0.0, "reason": "Not XML"}

    @staticmethod
    def _cef_detector(raw_content):
        first_content_line = ""

        for line in raw_content.splitlines():
            line = line.strip()

            if line and not line.startswith("#"):
                first_content_line = line
                break

        if first_content_line.startswith("CEF:"):
            return {
                "score": 0.99,
                "reason": "CEF prefix identified"
            }

        return {"score": 0.0, "reason": "Not CEF"}

    @staticmethod
    def _leef_detector(raw_content):
        first_content_line = ""

        for line in raw_content.splitlines():
            line = line.strip()

            if line and not line.startswith("#"):
                first_content_line = line
                break

        if first_content_line.startswith("LEEF:"):
            return {
                "score": 0.99,
                "reason": "LEEF prefix identified"
            }

        return {"score": 0.0, "reason": "Not LEEF"}

    @staticmethod
    def _syslog_detector(raw_content):
        first_content_line = ""

        for line in raw_content.splitlines():
            line = line.strip()

            if line and not line.startswith("#"):
                first_content_line = line
                break

        syslog_pattern = (
            r"^(?:<\d+>)?[A-Z][a-z]{2}\s+"
            r"\d{1,2}\s+"
            r"\d{2}:\d{2}:\d{2}\s+"
            r"\S+\s+"
        )

        if re.match(syslog_pattern, first_content_line):
            return {
                "score": 0.94,
                "reason": "Syslog timestamp and host pattern detected"
            }

        return {"score": 0.0, "reason": "Not syslog"}

    @staticmethod
    def _keyvalue_detector(raw_content):
        first_content_line = ""

        for line in raw_content.splitlines():
            line = line.strip()

            if line and not line.startswith("#"):
                first_content_line = line
                break

        if "=" in first_content_line and re.search(r"\w+\s*=", first_content_line):
            return {
                "score": 0.76,
                "reason": "Key/value structure detected"
            }

        return {"score": 0.0, "reason": "Not key:value format"}

    @staticmethod
    def _csv_detector(raw_content):
        lines = [line.strip() for line in raw_content.splitlines() if line.strip()]

        if len(lines) >= 2 and "," in lines[0]:
            return {
                "score": 0.72,
                "reason": "CSV header pattern detected"
            }

        return {"score": 0.0, "reason": "Not CSV"}

    @staticmethod
    def detect_with_confidence(raw_content: str):
        raw_content = (raw_content or "").strip()

        if not raw_content:
            return {
                "detected_format": "UNKNOWN",
                "confidence": 0.0,
                "parser_used": "fallback_parser",
                "score_breakdown": {},
                "details": {}
            }

        detectors = [
            ("JSON", FormatDetector._json_detector),
            ("XML", FormatDetector._xml_detector),
            ("CEF", FormatDetector._cef_detector),
            ("LEEF", FormatDetector._leef_detector),
            ("SYSLOG", FormatDetector._syslog_detector),
            ("KEYVALUE", FormatDetector._keyvalue_detector),
            ("CSV", FormatDetector._csv_detector),
        ]

        results = []

        for detector_name, detector_func in detectors:
            detector_result = detector_func(raw_content)

            if detector_result.get("score", 0.0) > 0:
                results.append({
                    "detector": detector_name,
                    "score": ConfidenceEngine.normalize(detector_result["score"]),
                    "reason": detector_result.get("reason", "")
                })

        if not results:
            return {
                "detected_format": "UNKNOWN",
                "confidence": 0.0,
                "parser_used": "fallback_parser",
                "score_breakdown": {},
                "details": {}
            }

        scored = ConfidenceEngine.score_results(results)

        detected_format = scored["detected_format"]

        return {
            "detected_format": detected_format,
            "confidence": scored["confidence"],
            "parser_used": (
                "fallback_parser"
                if detected_format == "UNKNOWN"
                else f"{detected_format.lower()}_parser"
            ),
            "score_breakdown": scored["score_breakdown"],
            "details": scored["details"]
        }

    @staticmethod
    def detect(raw_content: str) -> str:
        return FormatDetector.detect_with_confidence(raw_content)["detected_format"]