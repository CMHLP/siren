from __future__ import annotations
from typing import Any, TYPE_CHECKING
import importlib
import pathlib

if TYPE_CHECKING:
    from siren.core.scraper import ScraperProto

root = pathlib.Path("siren/scrapers")

SCRAPERS: dict[str, type[ScraperProto[Any]]] = {}

for path in root.glob("**/*.py"):
    dot = ".".join(path.parts)[:-3]
    module = importlib.import_module(dot)
    for scraper in getattr(module, "__all__", []):
        partialdot = ".".join(path.parts[2:])[:-3]
        SCRAPERS[f"{partialdot}.{scraper}"] = getattr(module, scraper)
