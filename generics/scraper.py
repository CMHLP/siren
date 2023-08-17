from datetime import datetime
from typing import Protocol

from .cloud import File, Cloud


class BaseScraper(Protocol):
    def __init__(self, start: datetime, end: datetime, cloud: Cloud):
        """Scrapes and returns a single CSV file containing the scraped data."""
        raise NotImplementedError

    def scrape(self):
        ...
