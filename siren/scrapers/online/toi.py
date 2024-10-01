from datetime import datetime
from typing import ClassVar
from yarl import URL
from siren.core import BaseScraper, Model
import asyncio
from asyncio import Task
from siren.utils import HTMLRE


__all__ = ("TOIOnlineScraper",)


class RawTOIOnlineArticle(Model):
    id: int
    hl: str
    wu: str
    dl: datetime
    syn: str = "-"

    @property
    def datetime(self):
        return self.dl.replace(tzinfo=None)

    @property
    def headline(self):
        return HTMLRE.sub("", self.hl)

    @property
    def synopsis(self):
        return HTMLRE.sub("", self.syn)

    @property
    def url(self):
        return self.wu


class TOIOnlineArticle(RawTOIOnlineArticle):

    FIELDS: ClassVar = ["id", "url", "datetime", "keyword", "headline", "synopsis"]
    keyword: str


class TOIOnlineSearchPage(Model):
    totalcount: int
    currentPageItemCount: int
    items: list[RawTOIOnlineArticle]


class TOIOnlineScraper(BaseScraper[TOIOnlineArticle]):

    def get_url(self, keyword: str, page: int = 1, chunk_size: int = 100) -> URL:
        return URL(
            f"https://toifeeds.indiatimes.com/treact/feeds/toi/web/show/topic?path=/topic/{keyword}/news&row={chunk_size}&curpg={page}"
        )

    async def search_keyword(self, keyword: str):
        page = 1
        articles: list[TOIOnlineArticle] = []
        while True:
            url = self.get_url(keyword, page=page)
            resp = await self.http.get(str(url))
            data = TOIOnlineSearchPage(**resp.json().get("contentsData", {}))
            if not data.items:
                break

            for item in data.items:
                if (
                    self.start.replace(tzinfo=None)
                    < item.datetime
                    < self.end.replace(tzinfo=None)
                ):
                    article = TOIOnlineArticle(**item.model_dump(), keyword=keyword)
                    articles.append(article)

            page += 1

        return articles

    async def scrape(self) -> list[TOIOnlineArticle]:
        tasks: list[Task[list[TOIOnlineArticle]]] = []
        for kw in self.keywords:
            task = asyncio.create_task(self.search_keyword(kw))
            tasks.append(task)
        return [article for chunk in await asyncio.gather(*tasks) for article in chunk]
