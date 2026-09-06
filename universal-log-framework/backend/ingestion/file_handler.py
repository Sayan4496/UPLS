import json


async def read_uploaded_file(file):

    content = await file.read()

    try:
        decoded_content = content.decode("utf-8")

    except UnicodeDecodeError:

        raise ValueError(
            "File must be UTF-8 encoded"
        )

    return decoded_content


def parse_json_content(content: str):

    try:

        data = json.loads(content)

        # If single JSON object
        if isinstance(data, dict):

            return [data]

        # If JSON array
        elif isinstance(data, list):

            return data

        else:

            raise ValueError(
                "Unsupported JSON structure"
            )

    except json.JSONDecodeError:

        raise ValueError(
            "Invalid JSON file"
        )