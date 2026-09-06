import shlex

from parsers.base_parser import BaseParser


class KeyValueParser(BaseParser):

    def parse(self, raw_content: str):

        events = []


        lines = raw_content.strip().splitlines()


        for line in lines:

            line = line.strip()


            if not line:

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


            except ValueError:

                continue


        return events