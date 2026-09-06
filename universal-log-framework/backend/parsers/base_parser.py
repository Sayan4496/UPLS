from abc import ABC, abstractmethod


class BaseParser(ABC):

    @abstractmethod
    def parse(self, raw_content: str) -> dict:
        """
        Parse raw log content and return structured data.
        """

        pass