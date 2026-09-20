from parsers.builtin._legacy import LineAwareLegacyAdapter
from parsers.leef_parser import LEEFParser as LegacyLEEFParser
from registry.parser_registry import register_parser


@register_parser
class LEEFParser(LineAwareLegacyAdapter):
    name = "LEEFParser"
    supported_formats = ["LEEF"]
    version = "1.0.0"
    detect_score = 0.99
    legacy_parser_class = LegacyLEEFParser
