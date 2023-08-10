from datetime import datetime
from typing import Protocol

from .cloud import File


class BaseScraper(Protocol):
    def scrape(self, start: datetime, end: datetime) -> File:
        """Scrapes and returns a single CSV file containing the scraped data."""
        raise NotImplementedError
