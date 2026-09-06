ALLOWED_EXTENSIONS = {
    ".json",
    ".csv",
    ".xml",
    ".cef",
    ".leef",
    ".keyvalue",
    ".log",
    ".syslog",
    ".txt"
}


def validate_file(filename: str):

    if not filename:
        raise ValueError("Filename is required")

    filename = filename.lower()

    for extension in ALLOWED_EXTENSIONS:

        if filename.endswith(extension):
            return True

    raise ValueError(
        "Unsupported file format. "
        "Allowed formats: JSON, CSV, XML, CEF, LEEF, KEYVALUE, LOG, SYSLOG, TXT"
    )