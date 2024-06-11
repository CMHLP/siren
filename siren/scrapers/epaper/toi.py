import asyncio
import json
import csv
from io import StringIO
from datetime import datetime
from json import JSONDecodeError
from typing import Any, ClassVar
import logging

from siren.core import File, BaseScraper, Model

import pydantic

from siren.core.http import ClientProto

logger = logging.getLogger(__name__)

__all__ = ("TOIScraper",)


class Edition(pydantic.BaseModel):
    date: datetime
    edition_code: str
    publication_code: str
    edition_name: str

    @pydantic.validator("date", pre=True)
    def convert_dt(cls, raw: str) -> datetime:
        return datetime.strptime(raw, "%Y-%m-%d")


class Article(Model):

    FIELDS: ClassVar = (
        "title",
        "page_title",
        "body",
        "page",
        "updatedAt",
        "edition_name",
        "date",
        "publication_code",
        "image",
    )

    _id: str
    article_id: str
    edition_id: str
    page: str
    type: int
    __v: int  # type: ignore
    author: str
    blurb: str | None = None
    body: str
    column_title: str
    createdAt: datetime | None = None
    location: str
    page_name: str = ""
    page_title: str = ""
    title: str
    updatedAt: datetime
    epaper_view: str
    score: float
    edition_details: Edition

    @pydantic.validator("createdAt", "updatedAt", pre=True)
    def convert_iso_dt(cls, raw: str):
        return datetime.fromisoformat(raw)

    @property
    def url(self) -> str:
        return f"https://epaper.timesgroup.com/article-share?article={self.page_name}_{self.edition_details.publication_code}"

    @property
    def publication_code(self) -> str:
        return self.edition_details.publication_code

    @property
    def edition_name(self) -> str:
        return self.edition_details.edition_name

    @property
    def date(self):
        return self.edition_details.date.strftime("%d/%m/%Y")

    @property
    def image(self):
        year, _month, _day, *_ = self.edition_details.date.timetuple()
        day = f"{_day:02}"
        month = f"{_month:02}"
        page = f"{int(self.page):03}"
        return f"https://asset.harnscloud.com/PublicationData/{self.publication_code}/{self.edition_details.edition_code}/{year}/{month}/{day}/Page/{day}_{month}_{year}_{page}_{self.edition_details.edition_code}.jpg"


class SearchResult(pydantic.BaseModel):
    totalDocs: int
    data: list[Article]
    page: int


class Search:
    url = "https://epsearch.harnscloud.com/api/v1/epaper/search"

    """Class to handle querying the search API and pagination"""

    def __init__(
        self,
        *,
        include_all: list[str] = [],
        exclude_all: list[str] = [],
        include_exact: str = "",
        include_any: list[str] = [],
        byline: str = "",
        location: str = "",
        type: str = "article",
        sort: str = "relevance",
        all_editions: bool = True,
        edition_code: list[str] = ["All"],
        limit: int = 50,
        page_title: str = "",
        client: ClientProto,
        start: datetime | None = None,
        end: datetime | None = None,
    ):
        self.client = client
        self.start = start or datetime.now()
        self.end = end or datetime.now()

        def join(s: list[str]):
            return ", ".join(s)

        self.data: dict[str, Any] = {
            "allOfThese": join(include_all),
            "exactPhrase": include_exact,
            "anyOfThese": join(include_any),
            "excludeThese": join(exclude_all),
            "byline": byline,
            "location": location,
            "fromDate": self._fmt_dt(self.start),
            "toDate": self._fmt_dt(self.end),
            "type": type,
            "sortBy": sort,
            "allEditions": all_editions,
            "editionCode": edition_code,
            "limit": limit,
            "pageTitle": page_title,
        }

    @staticmethod
    def _fmt_dt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")

    async def get_page(self, page_no: int = 1):
        """Return a `SearchResult` for a single page."""
        copy = dict(page=page_no)
        copy.update(self.data)
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://bcclepaper.indiatimes.com/",
            "Content-Type": "application/json",
            "Origin": "https://bcclepaper.indiatimes.com",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "TE": "trailers",
            "Host": "epsearch.harnscloud.com",
            "Cache-Control": "no-cache",
        }
        resp = await self.client.post(
            self.url, json=copy, headers=headers, timeout=None
        )
        try:
            data = resp.json()
            return SearchResult(**data, page=page_no)
        except (pydantic.ValidationError, JSONDecodeError) as e:
            logger.error(
                f"Ignoring exception {e} \n Response: {resp.status_code} {resp.text}"
            )

    async def get_all(self) -> list[Article]:
        """Calculate total pages and return a list of the obtained `Article`"""
        initial = await self.get_page()
        if not initial:
            logger.error(f"Could not find any articles for {self}!")
            return []
        pages = (initial.totalDocs // self.data["limit"]) + 2
        tasks: list[asyncio.Task[SearchResult | None]] = []
        for i in range(2, pages + 1):
            coro = self.get_page(page_no=i)
            task = asyncio.create_task(coro)
            tasks.append(task)
        data = [initial, *await asyncio.gather(*tasks)]
        articles = [article for sr in data for article in getattr(sr, "data", [])]
        if len(articles) != initial.totalDocs:
            logger.error(
                f"Obtained only {len(articles)}/{initial.totalDocs} articles for {repr(self)}!"
            )
        return articles

    def __repr__(self):
        return f"<Search({self.data['fromDate']} to {self.data['toDate']})>"


class TOIScraper(BaseScraper[Article]):
    async def scrape(self):
        tasks: list[asyncio.Task[list[Article]]] = []
        for term in self.keywords:
            exclude = ["bomb"]
            search = Search(
                client=self.http,
                include_any=[term],
                exclude_all=exclude,
                start=self.start,
                end=self.end,
                limit=50,
            )
            task = asyncio.create_task(search.get_all())
            tasks.append(task)
        chunks = await asyncio.gather(*tasks)
        return [article for chunk in chunks for article in chunk]

    async def _to_file(self):
        data = await self.scrape()
        headers = list(Article.model_fields) + list(Edition.model_fields)

        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(headers)
        for article in data:
            row: list[str | None] = []
            for key in Article.model_fields:
                row.append(getattr(article, key, None))

            for key in Edition.model_fields:
                row.append(getattr(article.edition_details, key, None))

            writer.writerow(row)

        f.seek(0)

        fmt = "%d-%m-%Y"
        return File(
            f.read().encode(),
            f"TOI_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
        )
