from yarl import URL
import asyncio
from io import StringIO
from logging import getLogger
from datetime import datetime
from siren.core import BaseScraper, Model

from pydantic import Field

__all__ = ("NMScraper",)

logger = getLogger(__name__)


class Story(Model):
    text: str = ""


class Card(Model):
    story_elements: list[Story] = Field(alias="story-elements")


class NMArticle(Model):
    url: str
    author_name: str = Field(alias="author-name")
    headline: str
    subheadline: str | None = None
    published_at: datetime = Field(alias="published-at")
    cards: list[Card]

    @property
    def text(self) -> str:
        return "\n".join(
            story.text for card in self.cards for story in card.story_elements
        )


class SearchResult(Model):
    total: int = 0
    items: list[NMArticle]


class NMScraper(BaseScraper[NMArticle]):
    BASE_URL = URL("https://www.thenewsminute.com/api/v1/advanced-search")

    PAGE_SIZE = 100

    def build_url(
        self,
        *,
        q: str,
        limit: int,
        offset: int,
        fields: list[str] = [
            "url",
            "author-name",
            "headline",
            "subheadline",
            "published-at",
            "cards",
        ],
    ):
        return self.BASE_URL % {
            "q": f'"{q}"',
            "limit": limit,
            "offset": offset,
            "fields": ",".join(fields),
        }

    async def fetch(self, *, q: str, limit: int, offset: int) -> SearchResult:
        url = self.build_url(q=q, limit=limit, offset=offset)
        logger.debug(f"GET {url}")
        resp = await self.http.get(str(url))
        data = resp.json()
        if data.get("error"):
            return SearchResult(total=0, items=[])
        return SearchResult(**data)

    async def fetch_all(self, *, q: str) -> list[NMArticle]:
        data: list[NMArticle] = []
        initial = await self.fetch(q=q, limit=self.PAGE_SIZE, offset=0)
        data.extend(
            [a for a in initial.items if self.start < a.published_at < self.end]
        )
        pages = (initial.total // self.PAGE_SIZE) - 1
        tasks: list[asyncio.Task[SearchResult]] = []
        for i in range(1, pages - 1):
            task = asyncio.create_task(
                self.fetch(q=q, limit=self.PAGE_SIZE, offset=self.PAGE_SIZE * i)
            )
            tasks.append(task)

        for fut in asyncio.as_completed(tasks):
            sr = await fut
            data.extend([a for a in sr.items if self.start < a.published_at < self.end])

        return data

    async def scrape(self) -> list[NMArticle]:
        tasks: list[asyncio.Task[list[NMArticle]]] = []
        for keyword in self.keywords:
            task = asyncio.create_task(self.fetch_all(q=keyword))
            tasks.append(task)
        return [article for chunk in await asyncio.gather(*tasks) for article in chunk]

    async def to_csv(
        self,
        *,
        include: set[str] = {"text"},
        exclude: set[str] = {"cards", "author_name"},
        aliases: dict[str, str] = {},
    ) -> StringIO:
        return await super().to_csv(include=include, exclude=exclude, aliases=aliases)
