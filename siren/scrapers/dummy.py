from siren.core import BaseScraper, Model
from logging import getLogger

logger = getLogger(__name__)

__all__ = ("DummyScraper",)


class DummyModel(Model):
    data: str | None = None


class DummyScraper(BaseScraper[DummyModel]):

    async def scrape(self):
        logger.debug(self.keywords)
        return [DummyModel(data="Dummy Sample A"), DummyModel(data="Dummy Sample B")]
