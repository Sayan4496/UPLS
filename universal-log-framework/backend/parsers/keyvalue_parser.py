import shlex

from parsers.base_parser import BaseParser


class KeyValueParser(BaseParser):

    format_name = "KEYVALUE"
    version = "1.0.0"

    def parse(self, raw_content: str):

        events = []
        self.parse_errors = []
        self.skipped_line_count = 0


        lines = raw_content.strip().splitlines()


        for line in lines:

            line = line.strip()


            if not line:

                continue

            if line.startswith("#"):

                continue


            event = {}


            try:

                pairs = shlex.split(line)


                for pair in pairs:

                    if "=" not in pair:

                        continue


                    key, value = pair.split(
                        "=",
                        1
                    )


                    event[key.strip()] = (
                        value.strip()
                    )


                if event:

                    events.append(event)
                else:
                    self.skipped_line_count += 1
                    self.parse_errors.append(
                        "Malformed Key-Value line: no key=value pairs found"
                    )


            except ValueError as error:

                self.skipped_line_count += 1
                self.parse_errors.append(
                    f"Malformed Key-Value line: {error}"
                )
                continue


        return events