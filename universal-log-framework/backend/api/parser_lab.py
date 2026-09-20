import json
import re
from dataclasses import asdict

from fastapi import APIRouter, Body

from normalization.normalizer import LogNormalizer
from registry.parser_registry import ParserRegistry, detect_best_parser


router = APIRouter(
    prefix="/parser-lab",
    tags=["Parser Lab"]
)


def extract_attributes(parsed_data, raw_content):

    attributes = {}

    for key in ["hostname", "host", "program", "process", "pid", "username", "user"]:
        value = parsed_data.get(key)
        if value not in [None, ""]:
            attributes[key] = value

    username_match = re.search(
        r"(?:for|user(?:name)?)\s+([A-Za-z0-9_.-]+)",
        str(parsed_data.get("message", raw_content)),
        re.IGNORECASE
    )

    if username_match and "username" not in attributes:
        attributes["username"] = username_match.group(1)

    return attributes


@router.get("/plugins")
def list_parser_plugins():

    return {
        "plugins": ParserRegistry.list_parsers()
    }


@router.post("/preview")
def preview_log(payload: dict = Body(...)):

    raw_content = str(payload.get("raw_log", ""))

    if not raw_content.strip():
        return {
            "raw_log": "",
            "parser": None,
            "normalized": None,
            "attributes": {},
            "error": "Paste a log entry to begin parsing."
        }

    parser_match = detect_best_parser(raw_content.encode("utf-8"))
    parser = parser_match.parser
    source_format = parser.supported_formats[0] if parser.supported_formats else "UNKNOWN"
    fallback_used = parser.name == "FallbackParser"
    parser_name = "fallback_parser" if fallback_used else parser.name

    if fallback_used:
        return {
            "raw_log": raw_content,
            "parsed_data": None,
            "parser": {
                "name": "FallbackParser",
                "parser_used": parser_name,
                "source_format": source_format,
                "confidence": parser_match.confidence,
                "fallback_used": fallback_used,
                "score_breakdown": parser_match.score_breakdown,
            },
            "normalized": None,
            "attributes": {},
            "status": "unsupported",
            "error": "Unable to identify a supported log format"
        }

    try:
        parsed_events, skipped_line_count, parse_errors = parser.parse(raw_content.encode("utf-8"))
        if not parsed_events:
            raise ValueError(parse_errors[0] if parse_errors else "Parser produced zero events")

        parsed_data = parser.normalize(parsed_events[0])
        normalized_data = asdict(LogNormalizer().normalize(parsed_data))
        normalized_data = json.loads(json.dumps(normalized_data, default=str))

        if parsed_data.get("hostname"):
            normalized_data["hostname"] = parsed_data["hostname"]
        if parsed_data.get("program"):
            normalized_data["process"] = parsed_data["program"].strip()
        if parsed_data.get("pid"):
            normalized_data["pid"] = parsed_data["pid"]

        if "username" in extract_attributes(parsed_data, raw_content):
            normalized_data["username"] = extract_attributes(parsed_data, raw_content)["username"]

        if parsed_data.get("message") and re.search(
            r"failed password|authentication failure|login failed",
            parsed_data["message"],
            re.IGNORECASE
        ):
            normalized_data["severity"] = "WARNING"
            normalized_data["event_type"] = "authentication_failure"

        return {
            "raw_log": raw_content,
            "parsed_data": parsed_data,
            "parser": {
                "name": parser.__class__.__name__,
                "parser_used": parser_name,
                "source_format": source_format,
                "confidence": parser_match.confidence,
                "fallback_used": fallback_used,
                "score_breakdown": parser_match.score_breakdown,
                "skipped_line_count": skipped_line_count,
                "parse_errors": parse_errors,
            },
            "normalized": normalized_data,
            "attributes": extract_attributes(parsed_data, raw_content)
        }

    except Exception:
        return {
            "raw_log": raw_content,
            "parsed_data": None,
            "parser": {
                "name": parser.__class__.__name__,
                "parser_used": parser_name,
                "source_format": source_format,
                "confidence": parser_match.confidence,
                "fallback_used": fallback_used,
                "score_breakdown": parser_match.score_breakdown,
            },
            "normalized": None,
            "attributes": {},
            "status": "unsupported",
            "error": "Unable to identify a supported log format"
        }