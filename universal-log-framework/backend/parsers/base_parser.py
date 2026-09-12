from abc import ABC, abstractmethod


class BaseParser(ABC):

    format_name = ""
    version = "1.0.0"

    @abstractmethod
    def parse(self, raw_content: str):
        """
        Parse raw log content and return structured data.
        """

        raise NotImplementedError

    def detect(self, raw_log: str) -> bool:
        """
        Return True when the parser can handle the supplied raw payload.
        """

        try:
            parsed_data = self.parse(raw_log)
            return self.validate(parsed_data)

        except Exception:
            return False

    def validate(self, parsed_data) -> bool:
        """
        Validate parsed content and ensure the parser produced usable events.
        """

        if parsed_data is None:
            return False

        if isinstance(parsed_data, (list, tuple)):
            return len(parsed_data) > 0

        if isinstance(parsed_data, dict):
            return bool(parsed_data)

        return True