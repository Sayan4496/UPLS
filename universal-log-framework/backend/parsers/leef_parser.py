from parsers.base_parser import BaseParser


class LEEFParser(BaseParser):

    format_name = "LEEF"
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

            # Only process LEEF events
            if not line.startswith("LEEF:"):
                continue

            parts = line.split("|", 5)

            if len(parts) < 6:
                continue

            version = parts[0].replace(
                "LEEF:",
                ""
            ).strip()

            event = {

                "leef_version": version,

                "vendor": parts[1].strip(),

                "product": parts[2].strip(),

                "product_version": parts[3].strip(),

                "event_id": parts[4].strip()

            }

            extensions = parts[5].strip()

            # LEEF fields are normally tab-separated
            pairs = extensions.split("\t")

            for pair in pairs:

                if "=" not in pair:
                    continue

                key, value = pair.split("=", 1)

                key = key.strip()

                value = value.strip()

                event[key] = value


            # -----------------------------------
            # STANDARD FIELD MAPPING
            # -----------------------------------

            # Timestamp
            event["timestamp"] = (

                event.get("devTime")

                or event.get("start")

                or event.get("end")

                or event.get("timestamp")

                or ""
            )


            # Source IP
            event["source_ip"] = (

                event.get("src")

                or event.get("srcIP")

                or event.get("source")

                or event.get("sourceAddress")

                or ""
            )


            # Destination IP
            event["destination_ip"] = (

                event.get("dst")

                or event.get("dstIP")

                or event.get("destination")

                or event.get("destinationAddress")

                or ""
            )


            # Event Type
            event["event_type"] = (

                event.get("cat")

                or event.get("eventType")

                or event.get("type")

                or event.get("name")

                or event.get("product")

                or "UNKNOWN"
            )


            # Severity
            event["severity"] = (

                event.get("sev")

                or event.get("severity")

                or "UNKNOWN"
            )


            # Action
            event["action"] = (

                event.get("action")

                or event.get("act")

                or "UNKNOWN"
            )


            # Message
            event["message"] = (

                event.get("msg")

                or event.get("message")

                or event.get("description")

                or event.get("event_name")

                or "No message"
            )


            events.append(event)

        return events