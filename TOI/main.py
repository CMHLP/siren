import asyncio
import csv
import os
import json
from io import StringIO
import time
from datetime import datetime
from typing import Any


from generics.cloud import Cloud, Drive, File
from generics.scraper import BaseScraper

import httpx
import pydantic


class Edition(pydantic.BaseModel):
    date: datetime
    edition_code: str
    publication_code: str
    edition_name: str

    @pydantic.validator("date", pre=True)
    def convert_dt(cls, raw: str) -> datetime:
        return datetime.strptime(raw, "%Y-%m-%d")


class Article(pydantic.BaseModel):
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


class SearchResult(pydantic.BaseModel):
    totalDocs: int
    data: list[Article]
    page: int


class Search:
    url = "https://epsearch.harnscloud.com/api/v1/epaper/search"

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
        edition_code: str = "All",
        limit: int = 50,
        page_title: str = "",
        client: httpx.AsyncClient,
        start: datetime | None = None,
        end: datetime | None = None,
    ):
        self.client = client
        self.start = start or datetime.now()
        self.end = end or datetime.now()

        join = lambda s: ", ".join(s)

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
        copy = dict(page=page_no)
        copy.update(self.data)
        resp = await self.client.post(self.url, data=copy)
        data = resp.json()
        if isinstance(data, str):
            raise RuntimeError(
                f"Couldn't serialize incoming data to JSON: {data}\nResponse: {resp}"
            )
        return SearchResult(**data, page=page_no)

    async def get_all(self) -> list[Article]:
        initial = await self.get_page()
        pages = (initial.totalDocs // self.data["limit"]) + 1
        tasks: list[asyncio.Task[SearchResult]] = []
        for i in range(2, pages + 1):
            coro = self.get_page(page_no=i)
            task = asyncio.create_task(coro)
            tasks.append(task)
        data = await asyncio.gather(*tasks)
        data.append(initial)
        articles = [article for sr in data for article in sr.data]
        if len(articles) != initial.totalDocs:
            raise RuntimeWarning(
                f"Obtained only {len(articles)}/{initial.totalDocs} articles for {repr(self)}!"
            )
        return articles

    def __repr__(self):
        return f"<Search({self.data['fromDate']} to {self.data['toDate']}>"


class TOIScraper(BaseScraper):
    def __init__(self, start: datetime, end: datetime, cloud: Cloud):
        self.start = start
        self.end = end
        self.cloud = cloud

    def scrape(self):
        file = asyncio.run(self._scrape())
        self.cloud.upload_file(file, "1tQs4MpKyco1F5UuxZnGO9Jj9IQHhGmEe")

    async def _scrape(self):
        terms = ["suicide"]
        exclude = ["bomb"]

        now = time.perf_counter()

        async with httpx.AsyncClient(timeout=None) as client:
            search = Search(
                client=client,
                include_any=terms,
                exclude_all=exclude,
                start=self.start,
                end=self.end,
                limit=50,
            )
            data = await search.get_all()
        print("Found: ", len(data))

        headers = list(Article.model_fields) + list(Edition.model_fields)

        f = StringIO()
        writer = csv.writer(f)
        writer.writerow(headers)
        for article in data:
            row = []
            for key in Article.model_fields:
                row.append(getattr(article, key, None))

            for key in Edition.model_fields:
                row.append(getattr(article.edition_details, key, None))

            writer.writerow(row)

        print(f"Finished in {time.perf_counter() - now}s")

        f.seek(0)

        fmt = "%d-%m-%Y"
        return File(
            f.read().encode(),
            f"TOI_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
        )
