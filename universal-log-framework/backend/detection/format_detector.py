from registry.parser_registry import detect_best_parser


class FormatDetector:
    """Backward-compatible facade over the pluggable parser registry."""

    @staticmethod
    def detect_with_confidence(raw_content: str):
        match = detect_best_parser((raw_content or "").encode("utf-8"))
        parser = match.parser
        detected_format = parser.supported_formats[0] if parser.supported_formats else "UNKNOWN"
        fallback_used = parser.name == "FallbackParser"
        return {
            "detected_format": detected_format,
            "confidence": match.confidence,
            "parser_used": "fallback_parser" if fallback_used else parser.name,
            "score_breakdown": match.score_breakdown,
            "details": {
                "parser": parser.name,
                "confidence": match.confidence,
            },
        }

    @staticmethod
    def detect(raw_content: str) -> str:
        return FormatDetector.detect_with_confidence(raw_content)["detected_format"]
