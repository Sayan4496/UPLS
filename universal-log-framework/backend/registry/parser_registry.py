import importlib
import inspect
import pkgutil

from parsers.base_parser import BaseParser


class FallbackParser(BaseParser):

    format_name = "FALLBACK"
    version = "1.0.0"

    def parse(self, raw_content: str):

        return [{
            "message": raw_content
        }]


class ParserRegistry:

    PARSERS = {}
    FALLBACK_PARSER = FallbackParser

    @classmethod
    def discover_parsers(cls):

        if cls.PARSERS:
            return cls.PARSERS

        import parsers

        package_path = getattr(
            parsers,
            "__path__",
            None
        )

        if package_path is None:
            return cls.PARSERS

        for module_info in pkgutil.iter_modules(package_path):

            module_name = module_info.name

            if module_name.startswith("_"):
                continue

            try:
                module = importlib.import_module(
                    f"parsers.{module_name}"
                )
            except Exception:
                continue

            for _, parser_class in inspect.getmembers(
                module,
                inspect.isclass
            ):

                if parser_class is BaseParser:
                    continue

                if parser_class is cls.FALLBACK_PARSER:
                    continue

                if not issubclass(parser_class, BaseParser):
                    continue

                if parser_class.__module__ != module.__name__:
                    continue

                format_name = getattr(
                    parser_class,
                    "format_name",
                    ""
                ).strip()

                if not format_name:
                    continue

                cls.PARSERS[format_name.upper()] = parser_class

        return cls.PARSERS


    @classmethod
    def register_parser(cls, parser_class):

        format_name = getattr(
            parser_class,
            "format_name",
            ""
        ).strip()

        if not format_name:
            raise ValueError(
                "Parser classes must define a format_name"
            )

        cls.PARSERS[format_name.upper()] = parser_class

        return parser_class


    @classmethod
    def list_parsers(cls):

        discovered_parsers = cls.discover_parsers()

        return [
            {
                "format": format_name,
                "class": parser_class.__name__,
                "version": getattr(
                    parser_class,
                    "version",
                    "1.0.0"
                )
            }
            for format_name, parser_class in sorted(
                discovered_parsers.items()
            )
        ]


    @classmethod
    def get_parser(cls, file_format: str):

        file_format = file_format.upper()

        parser_class = cls.discover_parsers().get(
            file_format
        )

        if parser_class is None:
            return cls.FALLBACK_PARSER()

        return parser_class()


# Backward compatibility with existing code

PARSER_REGISTRY = ParserRegistry.PARSERS


def get_parser(file_format: str):

    return ParserRegistry.get_parser(
        file_format
    )