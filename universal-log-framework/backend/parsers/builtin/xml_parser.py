from parsers.builtin._legacy import LegacyParserAdapter
from parsers.xml_parser import XMLParser as LegacyXMLParser
from registry.parser_registry import register_parser


@register_parser
class XMLParser(LegacyParserAdapter):
    name = "XMLParser"
    supported_formats = ["XML"]
    version = "1.0.0"
    detect_score = 0.83
    legacy_parser_class = LegacyXMLParser
