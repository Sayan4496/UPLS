import pytest

from ingestion.file_handler import read_uploaded_file
from parsers.json_parser import JSONParser
from parsers.builtin.cef_parser import CEFParser
from parsers.builtin.keyvalue_parser import KeyValueParser
from parsers.builtin.leef_parser import LEEFParser


def test_json_object_array_and_json_lines_parse(sample_logs):
    parser = JSONParser()
    assert len(parser.parse(sample_logs["json_object"])) == 1
    assert len(parser.parse(sample_logs["json_array"])) == 2
    assert len(parser.parse(sample_logs["json_lines"])) == 2


def test_malformed_json_raises_instead_of_returning_empty():
    with pytest.raises(ValueError, match="Invalid JSON"):
        JSONParser().parse('{"event_type":')


@pytest.mark.parametrize(
    "parser, payload",
    [
        (CEFParser(), "CEF:0|vendor|product"),
        (LEEFParser(), "LEEF:2.0|vendor|product"),
        (KeyValueParser(), 'src="unterminated'),
    ],
)
def test_malformed_line_does_not_report_success_with_zero_events(parser, payload):
    events, skipped_line_count, parse_errors = parser.parse(payload.encode("utf-8"))
    assert events == []
    assert skipped_line_count == 1
    assert parse_errors


@pytest.mark.parametrize("parser", [JSONParser(), CEFParser(), LEEFParser(), KeyValueParser()])
def test_empty_input_is_explicit(parser):
    if isinstance(parser, JSONParser):
        assert parser.parse("") == []
    else:
        events, skipped_line_count, parse_errors = parser.parse(b"")
        assert events == []
        assert skipped_line_count == 0
        assert parse_errors == []


@pytest.mark.parametrize("parser", [CEFParser(), LEEFParser(), KeyValueParser()])
def test_header_only_input_is_explicitly_empty(parser):
    events, skipped_line_count, parse_errors = parser.parse(b"# header only")
    assert events == []
    assert skipped_line_count == 0
    assert parse_errors == []


@pytest.mark.asyncio
async def test_invalid_utf8_is_rejected_cleanly():
    class UploadedFile:
        async def read(self):
            return b"\xff\xfe"

    with pytest.raises(ValueError, match="UTF-8"):
        await read_uploaded_file(UploadedFile())