from parsers.builtin._legacy import LineAwareLegacyAdapter
from parsers.cef_parser import CEFParser as LegacyCEFParser
from registry.parser_registry import register_parser


@register_parser
class CEFParser(LineAwareLegacyAdapter):
    name = "CEFParser"
    supported_formats = ["CEF"]
    version = "1.0.0"
    detect_score = 0.99
    legacy_parser_class = LegacyCEFParser
