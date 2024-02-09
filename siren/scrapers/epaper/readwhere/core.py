from __future__ import annotations
import asyncio
from datetime import datetime
from pydantic import ConfigDict
from yarl import URL
from logging import getLogger

from siren.core import Model, ClientProto, BaseScraper


logger = getLogger("siren")


class SearchResult(Model):
    """
    Represents a JSON search result from the search endpoint.

    Attributes
    ----------

    status: :class:`bool`
        Whether the search yielded results or not.

    numFound: :class:`int | None`
        The number of articles found, or None if the search was unsuccessful.

    start: :class:`int | None`
        The starting number of this page.

    to: :class:`int | None`
        The ending number of this page.

    data: :class:`list[Article]`
        The articles found by the search.

    """

    status: bool
    numFound: int | None = None
    start: int | None = None
    to: int | None = None
    data: list[Article] = []


class PartialArticle(Model):
    """
    Represents a partial Article obtained from the publishdates endpoint.

    Parameters
    ----------

    id: :class:`str`
        The Article ID

    published: :class:`datetime`
        The :class:`datetime.datetime` when the article was published.

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int | str
    published: datetime
    base_url: URL

    async def search_one(
        self, keyword: str, *, session: ClientProto
    ) -> SearchResult | None:
        """Search a single issue and return a :class:`SearchResult`"""
        url = self.base_url / f"search/issue/{self.id}/{keyword}"
        try:
            resp = await session.get(str(url))
        except Exception as e:
            logger.error(f"Ignoring exception {e}")
            return None
        data = resp.json()
        if "data" in data:
            for article in data["data"]:
                for field in self.model_fields:
                    article[field] = getattr(self, field, None)
        return SearchResult(**data)

    async def search_many(
        self, keywords: list[str], *, session: ClientProto
    ) -> list[SearchResult]:
        """Runs :class:`PartialArticle.search_one` concurrently for each given keyword."""
        tasks: list[asyncio.Task[SearchResult | None]] = []
        for term in keywords:
            task = asyncio.create_task(self.search_one(term, session=session))
            tasks.append(task)
        return [sr for sr in await asyncio.gather(*tasks) if sr and sr.status]


class Article(PartialArticle):
    pageNum: int | str | None = None
    excerpt: str
    issue_id: str
    title_id: str

    @property
    def url(self):
        return self.base_url / str(self.issue_id)


class BaseReadwhereScraper(BaseScraper[Article]):
    BASE_URL: URL
    EDITIONS: dict[str, str]

    model = Article

    async def get_partial_articles(
        self,
        edition_id: int | str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PartialArticle]:
        """
        Retrieves :class:`PartialArticle`s for the given edition ID. If `start` or `end` are passed here, they are prioritised over the scraper's start and end.

        Parameters
        ----------

        edition_id: :class:`int` | :class:`str`
            The Edition ID of the articles

        start: :class:`datetime.datetime` | `None` defaults to `None`
            The date and time to start scraping from.
            This parameter is for flexibility.

        end: :class:`datetime.datetime` | `None` defaults to `None`
            The date and time to stop scraping at.
            This parameter is for flexibility.

        Returns
        -------

        :class:`list[PartialArticle]`

        """
        start = start or self.start
        end = end or self.end
        url = (
            self.BASE_URL
            / f"viewer/publishdates/{edition_id}/{int(start.timestamp())}/{int(end.timestamp())}/json"
        )
        resp = await self.http.get(str(url))
        return [PartialArticle(**i, base_url=self.BASE_URL) for i in resp.json()]

    async def search_edition(self, edition_id: int | str) -> list[Article]:
        """Search an edition and return a list of :class:`Article`"""
        partials = await self.get_partial_articles(edition_id)
        ret: list[Article] = []
        for partial in partials:
            data = await partial.search_many(self.keywords, session=self.http)
            for sr in data:
                ret.extend(sr.data)
        return ret

    async def scrape(self) -> list[Article]:
        tasks: list[asyncio.Task[list[Article]]] = []
        for edition_id in self.EDITIONS:
            task = asyncio.create_task(self.search_edition(edition_id))
            tasks.append(task)
        data = [article for chunk in await asyncio.gather(*tasks) for article in chunk]
        return data

    async def to_csv(
        self,
        *,
        include: set[str] = set(),
        exclude: set[str] = set(),
        aliases: dict[str, str] = {},
    ):
        include.add("url")
        exclude.add("base_url")
        return await super().to_csv(include=include, exclude=exclude, aliases=aliases)
