from parsers.builtin._legacy import LegacyParserAdapter
from parsers.syslog_parser import SyslogParser as LegacySyslogParser
from registry.parser_registry import register_parser


@register_parser
class SyslogParser(LegacyParserAdapter):
    name = "SyslogParser"
    supported_formats = ["SYSLOG"]
    version = "1.0.0"
    detect_score = 0.94
    legacy_parser_class = LegacySyslogParser
