import re

from parsers.base_parser import BaseParser


class CEFParser(BaseParser):

    format_name = "CEF"
    version = "1.0.0"

    def parse(self, raw_content: str):

        events = []

        lines = raw_content.strip().splitlines()


        for line in lines:

            line = line.strip()


            # Skip empty lines

            if not line:
                continue


            # Skip comments

            if line.startswith("#"):
                continue


            # Only process CEF events

            if not line.startswith("CEF:"):
                continue


            parts = line.split("|", 7)


            if len(parts) < 8:
                continue


            version = parts[0].replace("CEF:", "").strip()


            event = {

                "cef_version": version,

                "vendor": parts[1].strip(),

                "product": parts[2].strip(),

                "device_version": parts[3].strip(),

                "signature_id": parts[4].strip(),

                "event_name": parts[5].strip(),

                "severity": parts[6].strip()

            }


            extensions = parts[7].strip()


            # Extract CEF extension fields

            matches = re.finditer(

                r'(\w+)=([^=]*?)(?=\s+\w+=|$)',

                extensions

            )


            for match in matches:

                key = match.group(1).strip()

                value = match.group(2).strip()

                event[key] = value


            # Add standard aliases

            if "src" in event:

                event["source_ip"] = event["src"]


            if "dst" in event:

                event["destination_ip"] = event["dst"]


            if "msg" in event:

                event["message"] = event["msg"]


            if "act" in event:

                event["action"] = event["act"]


            if "event_name" in event:

                event["event_type"] = event["event_name"]


            events.append(event)


        return events