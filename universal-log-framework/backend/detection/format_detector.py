import json
import re


class FormatDetector:

    @staticmethod
    def detect(raw_content: str) -> str:

        raw_content = raw_content.strip()


        if not raw_content:
            return "UNKNOWN"


        # Get first non-empty, non-comment line

        lines = raw_content.splitlines()

        first_content_line = ""


        for line in lines:

            line = line.strip()


            if line and not line.startswith("#"):

                first_content_line = line

                break


        # JSON Detection

        try:

            json.loads(raw_content)

            return "JSON"

        except Exception:

            pass


        # XML Detection

        if (
            first_content_line.startswith("<")
            and first_content_line.endswith(">")
        ):

            return "XML"


        # CEF Detection

        if first_content_line.startswith("CEF:"):

            return "CEF"


        # LEEF Detection

        if first_content_line.startswith("LEEF:"):

            return "LEEF"


        # SYSLOG Detection

        syslog_pattern = (

            r"^(?:<\d+>)?[A-Z][a-z]{2}\s+"

            r"\d{1,2}\s+"

            r"\d{2}:\d{2}:\d{2}\s+"

            r"\S+\s+"

        )


        if re.match(
            syslog_pattern,
            first_content_line
        ):

            return "SYSLOG"


        # KEYVALUE Detection

        if "=" in first_content_line:

            if re.search(
                r"\w+\s*=",
                first_content_line
            ):

                return "KEYVALUE"


        # CSV Detection

        if len(lines) >= 2:

            if "," in first_content_line:

                return "CSV"


        return "UNKNOWN"