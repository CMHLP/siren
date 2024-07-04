from datetime import datetime
from siren.core import BaseScraper, Model
from logging import getLogger

logger = getLogger(__name__)

__all__ = ("DummyScraper",)


class DummyModel(Model):
    data: str | None = None
    date: datetime


class DummyScraper(BaseScraper[DummyModel]):

    async def scrape(self):
        logger.debug(self.keywords)
        return [
            DummyModel(data="Dummy Sample A", date=datetime.now()),
            DummyModel(data="Dummy Sample B", date=datetime.now()),
        ]
