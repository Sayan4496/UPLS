import csv
from io import StringIO

from parsers.base_parser import BaseParser


class CSVParser(BaseParser):

    def parse(self, raw_content: str):

        try:

            raw_content = raw_content.strip()

            if not raw_content:
                return []

            csv_file = StringIO(raw_content)

            sample = raw_content[:4096]

            try:

                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t|"
                )

            except csv.Error:

                dialect = csv.excel


            reader = csv.DictReader(
                csv_file,
                dialect=dialect
            )

            events = []


            for row in reader:

                cleaned_row = {

                    str(key).strip().lower(): (
                        value.strip()
                        if isinstance(value, str)
                        else value
                    )

                    for key, value in row.items()

                    if key is not None

                }


                if any(
                    value not in [None, ""]
                    for value in cleaned_row.values()
                ):

                    events.append(cleaned_row)


            return events


        except Exception as e:

            raise ValueError(
                f"CSV parsing failed: {str(e)}"
            )