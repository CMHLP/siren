from __future__ import annotations
import asyncio
import csv
from datetime import datetime
from io import StringIO
from aiohttp import ClientSession
from pydantic import BaseModel, ConfigDict
from yarl import URL

from generics.cloud import File


class SearchResult(BaseModel):
    status: bool
    numFound: int | None = None
    start: int | None = None
    to: int | None = None
    data: list[Article] = []


class PartialArticle(BaseModel):
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

    id: str
    published: datetime
    base_url: URL

    async def search_one(self, keyword: str, *, session: ClientSession) -> SearchResult:
        url = self.base_url / f"search/issue/{self.id}/{keyword}"
        resp = await session.get(url)
        data = await resp.json()
        for article in data["data"]:
            article["published"] = self.published
        return SearchResult(**await resp.json())

    async def search_many(
        self, keywords: list[str], *, session: ClientSession
    ) -> list[SearchResult]:
        """Runs :class:`PartialArticle.search_one` concurrently for each given keyword."""
        tasks: list[asyncio.Task[SearchResult]] = []
        for term in keywords:
            task = asyncio.create_task(self.search_one(term, session=session))
            tasks.append(task)
        return [sr for sr in await asyncio.gather(*tasks) if sr.status]


class Article(PartialArticle):
    pageNum: str
    excerpt: str
    issue_id: str
    title_id: str


class ReadwhereScraper:
    """Base implementation of a scraper for readwhere-based websites (TNIE, Tribune, etc).

    Parameters
    ----------
    start: :class:`datetime.datetime`
        The :class:`datetime.datetime` to start scraping from.

    end: :class:`datetime.datetime`
        The :class:`datetime.datetime` to stop scraping at.

    keywords: :class:`list[str]`
        The keywords to search for.

    base_url: :class:`yarl.URL`
        The Base URL of the readwhere website.

    session: :class:`aiohttp.ClientSession`
        The ClientSession to use for making requests.

    """

    BASE_URL: URL
    EDITIONS: dict[str, str]

    def __init__(
        self,
        start: datetime,
        end: datetime,
        keywords: list[str],
        *,
        session: ClientSession,
    ):
        self.start = start
        self.end = end
        self.keywords = keywords
        self.session = session

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
        resp = await self.session.get(url)
        return [PartialArticle(**i, base_url=self.BASE_URL) for i in await resp.json()]

    async def search_edition(self, edition_id: int | str):
        partials = await self.get_partial_articles(edition_id)
        ret: list[Article] = []
        for partial in partials:
            data = await partial.search_many(self.keywords, session=self.session)
            for sr in data:
                ret.extend(sr.data)
        return ret

    async def scrape(self):
        tasks: list[asyncio.Task[list[Article]]] = []
        for edition_id, edition_name in self.EDITIONS.items():
            task = asyncio.create_task(self.search_edition(edition_id))
            tasks.append(task)
        data = [article for chunk in await asyncio.gather(*tasks) for article in chunk]
        print(data)
        headers = list(Article.model_fields) + ["name", "url"]
        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(headers)
        for article in data:
            row = []
            for key in headers:
                row.append(getattr(article, key, None))
            writer.writerow(row)
        f.seek(0)
        fmt = "%d-%m-%Y"
        return File(
            f.read().encode(),
            f"{self.__class__.__name__}_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
        )
