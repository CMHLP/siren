from __future__ import annotations
import asyncio
from typing import Self
import pytesseract  # type: ignore
from datetime import datetime
from pydantic import ConfigDict
from yarl import URL
from PIL import Image
from io import BytesIO
from logging import getLogger
from siren.core import Model, ClientProto, BaseScraper


logger = getLogger(__name__)


class SearchPageResult(Model):
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


class PageChunk(Model):
    tx: int
    ty: int
    width: int
    height: int
    url: str

    async def search(
        self, *, client: ClientProto, keywords: list[str]
    ) -> tuple[Self, list[str]]:
        """Return a list of strings found from the keywords list"""
        resp = await client.get(self.url)
        image = Image.open(BytesIO(resp.content))
        text: str = await asyncio.to_thread(pytesseract.image_to_string, image, timeout=10)  # type: ignore
        split = text.lower().split()
        items: list[str] = []
        for kw in keywords:
            for word in split:
                if kw.lower() == word.lower():
                    items.append(word)
        return self, items


class PageLevel(Model):
    width: int
    height: int
    chunks: list[PageChunk]


class Levels(Model):
    thumbs: PageLevel
    level0: PageLevel
    leveldefault: PageLevel
    level1: PageLevel
    level2: PageLevel
    header: PageLevel


class Page(Model):
    key: str
    pagenum: int
    levels: Levels

    async def search(self, *, keywords: list[str], client: ClientProto) -> PageResult:
        """Return a `PageResult` containing self (the page in which matches were found) and a mapping of url to a list of the matches found in the corresponding image."""
        target = self.levels.level2
        matches: dict[str, list[str]] = {}
        tasks: list[asyncio.Task[tuple[PageChunk, list[str]]]] = []
        for chunk in target.chunks:
            task = asyncio.create_task(chunk.search(keywords=keywords, client=client))
            tasks.append(task)
        for fut in asyncio.as_completed(tasks):
            chunk, found = await fut
            matches[chunk.url] = found
        return PageResult(page=self, matches=matches)


class PageResult(Model):
    page: Page
    matches: dict[str, list[str]]


class PageMeta(Model):
    pages: dict[str, Page]

    async def search(
        self, *, keywords: list[str], client: ClientProto
    ) -> list[PageResult]:
        tasks: list[asyncio.Task[PageResult]] = []
        for _page_number, page in self.pages.items():
            tasks.append(
                asyncio.create_task(page.search(keywords=keywords, client=client))
            )
        return await asyncio.gather(*tasks)


class Result(Model):
    pages: list[PageResult]
    partial: PartialArticle

    @property
    def date(self):
        return self.partial.published

    @property
    def edition(self):
        return self.partial.edition_name

    @property
    def url(self):
        return self.partial.url


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
    edition_id: int | str
    edition_name: str

    @property
    def url(self):
        return self.base_url / str(self.id)

    async def get_pagemeta(self, *, client: ClientProto) -> PageMeta:
        url = self.base_url / f"pagemeta/get/{self.id}/1-50"
        url %= {
            "type": "newspaper",
            "user": "2341985",
            "crypt": "313581a5b8d413a08e027161b18e2921857250ef",
            "key": "1711454980",
        }
        # TODO: Can we find a way around using these constants?
        resp = await client.get(str(url))
        return PageMeta(pages=resp.json())

    async def search(self, *, client: ClientProto, keywords: list[str]) -> Result:
        meta = await self.get_pagemeta(client=client)
        results = await meta.search(keywords=keywords, client=client)
        pages: list[PageResult] = []
        for res in results:
            if res.matches:
                pages.append(res)
        return Result(pages=pages, partial=self)

    async def search_one(
        self, keyword: str, *, client: ClientProto
    ) -> SearchPageResult | None:
        """
        Search a single issue and return a :class:`SearchPageResult`

        Parameters
        ----------

        keyword: :class:`str`
            The keyword to search.

        client: :class:`ClientProto`
            The HTTP Client to use.


        Returns
        -------

        :class:`SearchPageResult | None`

        A `SearchPageResult` if successful, else `None`

        """
        url = self.base_url / f"search/issue/{self.id}/{keyword}"
        try:
            resp = await client.get(str(url))
        except Exception as e:
            logger.error(f"Ignoring exception {e}")
            return None
        data = resp.json()
        if "data" in data:
            for article in data["data"]:
                for field in self.model_fields:
                    article[field] = getattr(self, field, None)
        return SearchPageResult(**data)

    async def search_many(
        self, keywords: list[str], *, client: ClientProto
    ) -> list[SearchPageResult]:
        """Runs :class:`PartialArticle.search_one` concurrently for each given keyword."""
        tasks: list[asyncio.Task[SearchPageResult | None]] = []
        for term in keywords:
            task = asyncio.create_task(self.search_one(term, client=client))
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


class BaseReadwhereScraper(BaseScraper[Result]):
    BASE_URL: URL
    EDITIONS: dict[str, str]

    model = Article

    async def get_partial_articles(
        self,
        edition_id: int | str,
        edition_name: str,
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
        return [
            PartialArticle(
                **i,
                edition_id=edition_id,
                edition_name=edition_name,
                base_url=self.BASE_URL,
            )
            for i in resp.json()
        ]

    async def _old_search_edition(
        self, edition_id: int | str, edition_name: str
    ) -> list[Article]:
        """Search an edition and return a list of :class:`Article`"""
        partials = await self.get_partial_articles(edition_id, edition_name)
        ret: list[Article] = []
        for partial in partials:
            data = await partial.search_many(self.keywords, client=self.http)
            for sr in data:
                ret.extend(sr.data)
        return ret

    async def search_edition(
        self, edition_id: int | str, edition_name: str
    ) -> list[Result]:
        partials = await self.get_partial_articles(edition_id, edition_name)
        logger.debug(f"Partials: {partials}")
        tasks: list[asyncio.Task[Result]] = []
        for partial in partials:
            task = asyncio.create_task(
                partial.search(client=self.http, keywords=self.keywords)
            )
            tasks.append(task)
            break
        return await asyncio.gather(*tasks)

    async def scrape(self) -> list[Result]:
        tasks: list[asyncio.Task[list[Result]]] = []
        for edition_id, edition_name in self.EDITIONS.items():
            task = asyncio.create_task(self.search_edition(edition_id, edition_name))
            tasks.append(task)
            break
        data = [article for chunk in await asyncio.gather(*tasks) for article in chunk]
        return data

        # tasks: list[asyncio.Task[list[Article]]] = []
        # for edition_id in self.EDITIONS:
        #     task = asyncio.create_task(self.search_edition(edition_id))
        #     tasks.append(task)
        # data = [article for chunk in await asyncio.gather(*tasks) for article in chunk]
        # return data

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
