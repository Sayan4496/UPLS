from parsers.base import BaseParser
from parsers.builtin._legacy import LegacyParserAdapter
from parsers.json_parser import JSONParser as LegacyJSONParser
from registry.parser_registry import register_parser


@register_parser
class JSONParser(LegacyParserAdapter):
    name = "JSONParser"
    supported_formats = ["JSON"]
    version = "1.0.0"
    detect_score = 0.96
    legacy_parser_class = LegacyJSONParser
