from datetime import datetime
from typing import Protocol, Sequence

from .cloud import Cloud


class BaseScraper(Protocol):
    start: datetime
    end: datetime
    cloud: Cloud
    keywords: Sequence[str]

    def __init__(
        self, start: datetime, end: datetime, cloud: Cloud, keywords: Sequence[str]
    ):
        raise NotImplementedError

    def scrape(self):
        ...
