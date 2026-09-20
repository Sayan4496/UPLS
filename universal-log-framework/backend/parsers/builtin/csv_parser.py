from parsers.builtin._legacy import LegacyParserAdapter
from parsers.csv_parser import CSVParser as LegacyCSVParser
from registry.parser_registry import register_parser


@register_parser
class CSVParser(LegacyParserAdapter):
    name = "CSVParser"
    supported_formats = ["CSV"]
    version = "1.0.0"
    detect_score = 0.72
    legacy_parser_class = LegacyCSVParser
