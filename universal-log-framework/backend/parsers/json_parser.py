import json

from parsers.base_parser import BaseParser


class JSONParser(BaseParser):

    format_name = "JSON"
    version = "1.0.0"

    def parse(self, raw_content: str):

        try:

            raw_content = raw_content.strip()


            if not raw_content:

                return []


            data = json.loads(raw_content)


            # JSON object

            if isinstance(data, dict):

                # Check common event containers

                for key in [
                    "events",
                    "logs",
                    "data",
                    "records"
                ]:

                    if key in data and isinstance(
                        data[key],
                        list
                    ):

                        return data[key]


                return [data]


            # JSON array

            if isinstance(data, list):

                return data


            return []


        except json.JSONDecodeError:

            # Try JSON Lines format

            events = []


            for line in raw_content.splitlines():

                line = line.strip()


                if not line:

                    continue


                try:

                    event = json.loads(line)


                    if isinstance(event, dict):

                        events.append(event)


                except json.JSONDecodeError:

                    continue


            if events:

                return events


            raise ValueError(
                "Invalid JSON log format"
            )