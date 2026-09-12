import re

from parsers.base_parser import BaseParser


class SyslogParser(BaseParser):

    format_name = "SYSLOG"
    version = "1.0.0"

    def parse(self, raw_content: str):

        events = []


        lines = raw_content.strip().splitlines()


        pattern = re.compile(

            r"^(?:<\d+>)?(?P<timestamp>"
            r"[A-Z][a-z]{2}\s+"
            r"\d{1,2}\s+"
            r"\d{2}:\d{2}:\d{2}"
            r")\s+"

            r"(?P<hostname>\S+)\s+"

            r"(?P<program>"
            r"[^\[:]+"
            r")"

            r"(?:\[(?P<pid>\d+)\])?"

            r":\s*"

            r"(?P<message>.*)$"

        )


        for line in lines:

            line = line.strip()


            if not line:

                continue


            match = pattern.match(line)


            if match:

                event = match.groupdict()


                if not event.get("message"):

                    event["message"] = "No message"


                events.append(event)


            else:

                if events and events[-1].get("message") == "No message":
                    events[-1]["message"] = line
                    continue

                # Store unmatched syslog line

                events.append({

                    "raw_log": line,

                    "message": line

                })


        return events