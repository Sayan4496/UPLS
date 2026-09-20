import importlib
import logging
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Type

import yaml

from parsers.base import BaseParser

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParserMatch:
    parser: BaseParser
    confidence: float
    score_breakdown: dict[str, float]


class FallbackParser(BaseParser):
    name = "FallbackParser"
    supported_formats = ["UNKNOWN"]
    version = "1.0.0"

    def detect(self, raw_sample: bytes) -> float:
        return 0.0

    def parse(self, raw_event: bytes):
        text = raw_event.decode("utf-8", errors="replace")
        return ([{"message": text}] if text else []), 0, []


_PARSERS: dict[str, Type[BaseParser]] = {}
_DISCOVERED = False


def register_parser(parser_class: Type[BaseParser]):
    if not issubclass(parser_class, BaseParser):
        raise TypeError("Registered parsers must extend BaseParser")
    if not parser_class.name or not parser_class.supported_formats:
        raise ValueError("Parsers must define name and supported_formats")
    _PARSERS[parser_class.name] = parser_class
    return parser_class


def _import_module(module_name: str) -> None:
    try:
        importlib.import_module(module_name)
    except Exception:
        logger.exception("Unable to load parser module %s", module_name)


def _discover_package(package_name: str) -> None:
    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)
    if package_path is None:
        return
    for module_info in pkgutil.walk_packages(package_path, f"{package_name}."):
        if not module_info.name.rsplit(".", 1)[-1].startswith("_"):
            _import_module(module_info.name)


def _discover_custom_plugins() -> None:
    custom_root = Path(__file__).resolve().parent.parent / "parsers" / "custom"
    for plugin_dir in sorted(path for path in custom_root.iterdir() if path.is_dir()):
        if (plugin_dir / "parser.py").exists():
            _import_module(f"parsers.custom.{plugin_dir.name}.parser")
            manifest_path = plugin_dir / "manifest.yaml"
            if manifest_path.exists():
                try:
                    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
                    for parser_class in _PARSERS.values():
                        if parser_class.__module__ == f"parsers.custom.{plugin_dir.name}.parser":
                            parser_class.manifest = manifest
                except Exception:
                    logger.exception("Unable to load parser manifest %s", manifest_path)


def discover_parsers() -> dict[str, Type[BaseParser]]:
    global _DISCOVERED
    if not _DISCOVERED:
        _discover_package("parsers.builtin")
        _discover_custom_plugins()
        _DISCOVERED = True
    return _PARSERS


def list_parsers() -> list[dict]:
    return [
        {
            "name": parser_class.name,
            "formats": parser_class.supported_formats,
            "class": parser_class.__name__,
            "version": getattr(parser_class, "version", "1.0.0"),
            "manifest": getattr(parser_class, "manifest", {}),
        }
        for parser_class in sorted(discover_parsers().values(), key=lambda item: item.name)
    ]


def get_parser(name: str) -> BaseParser:
    normalized = name.strip().lower()
    for parser_class in discover_parsers().values():
        if parser_class.name.lower() == normalized or any(
            supported.lower() == normalized for supported in parser_class.supported_formats
        ):
            return parser_class()
    return FallbackParser()


def detect_best_parser(raw_sample: bytes) -> ParserMatch:
    candidates = []
    for parser_class in discover_parsers().values():
        parser = parser_class()
        confidence = max(0.0, min(1.0, float(parser.detect(raw_sample))))
        if confidence > 0:
            candidates.append((confidence, parser.name, parser))

    # Ties are deterministic: highest confidence wins, then parser name.
    if not candidates:
        return ParserMatch(FallbackParser(), 0.0, {})
    candidates.sort(key=lambda item: (-item[0], item[1].lower()))
    best = candidates[0]
    return ParserMatch(
        parser=best[2],
        confidence=best[0],
        score_breakdown={name: score for score, name, _ in candidates},
    )


class ParserRegistry:
    PARSERS = _PARSERS
    FALLBACK_PARSER = FallbackParser
    discover_parsers = staticmethod(discover_parsers)
    register_parser = staticmethod(register_parser)
    list_parsers = staticmethod(list_parsers)
    get_parser = staticmethod(get_parser)
    detect_best_parser = staticmethod(detect_best_parser)


PARSER_REGISTRY = _PARSERS
