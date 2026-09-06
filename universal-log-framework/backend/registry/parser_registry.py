from parsers.json_parser import JSONParser
from parsers.csv_parser import CSVParser
from parsers.xml_parser import XMLParser
from parsers.syslog_parser import SyslogParser
from parsers.cef_parser import CEFParser
from parsers.leef_parser import LEEFParser
from parsers.keyvalue_parser import KeyValueParser


class ParserRegistry:

    PARSERS = {

        "JSON": JSONParser,

        "CSV": CSVParser,

        "XML": XMLParser,

        "SYSLOG": SyslogParser,

        "CEF": CEFParser,

        "LEEF": LEEFParser,

        "KEYVALUE": KeyValueParser

    }


    @classmethod
    def get_parser(cls, file_format: str):

        file_format = file_format.upper()

        parser_class = cls.PARSERS.get(
            file_format
        )

        if parser_class is None:

            raise ValueError(
                f"No parser found for format: {file_format}"
            )

        return parser_class()


# Backward compatibility with existing code

PARSER_REGISTRY = ParserRegistry.PARSERS


def get_parser(file_format: str):

    return ParserRegistry.get_parser(
        file_format
    )