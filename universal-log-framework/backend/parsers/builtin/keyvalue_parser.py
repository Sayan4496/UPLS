from parsers.builtin._legacy import LineAwareLegacyAdapter
from parsers.keyvalue_parser import KeyValueParser as LegacyKeyValueParser
from registry.parser_registry import register_parser


@register_parser
class KeyValueParser(LineAwareLegacyAdapter):
    name = "KeyValueParser"
    supported_formats = ["KEYVALUE"]
    version = "1.0.0"
    detect_score = 0.76
    legacy_parser_class = LegacyKeyValueParser
