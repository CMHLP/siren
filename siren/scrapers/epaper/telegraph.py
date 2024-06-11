from __future__ import annotations
from asyncio import Task
import asyncio
import re
from datetime import timedelta, datetime
import logging
from siren.core import BaseScraper, Model
from yarl import URL
from typing import TYPE_CHECKING
from bs4 import BeautifulSoup

from siren.core.http import ResponseProto


if TYPE_CHECKING:
    from siren.core import HTTP


__all__ = ("TGScraper",)

logger = logging.getLogger(__name__)


BASE_URL = URL("https://epaper.telegraphindia.com")
EDITIONS = {"calcutta": 71, "north bengal": 72, "south bengal": 73}
IMAGE_REGEX = re.compile(r"show_pop\('(\d+)','(\d+)','(\d+)'\)")


class TGPaper:
    def __init__(self, edition: str, edition_id: int, date: datetime, *, http: HTTP):
        self.edition = edition
        self.edition_id = edition_id
        self.date = date
        self.http = http

    async def scrape(self, page: int = 1):
        url = str(
            BASE_URL
            / self.edition
            / self.date.strftime("%Y-%m-%d")
            / str(self.edition_id)
            / f"Page-{page}.html"
        )
        resp = await self.http.get(url)
        tasks: list[Task[TGArticle]] = []
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        pages = 0
        if _element := soup.select_one("#totalpages"):
            if _value := _element.get("value"):
                assert isinstance(_value, str)
                pages = int(_value)
        for match in IMAGE_REGEX.finditer(html):
            paper_id, article_id, _ = match.groups()
            textview_url = str(
                BASE_URL
                / "textview"
                / paper_id
                / article_id
                / f"{self.edition_id}.html"
            )
            task = asyncio.create_task(
                TGArticle.from_textview(
                    textview_url, page=page, page_url=url, paper=self, pages=pages
                )
            )
            tasks.append(task)
        return await asyncio.gather(*tasks)

    async def search(self, keywords: list[str]):
        initial = await self.scrape()
        pages = initial[0].pages
        tasks: list[Task[list[TGArticle]]] = []
        for i in range(2, pages + 1):
            task = asyncio.create_task(self.scrape(i))
            tasks.append(task)
        articles = [
            *initial,
            *[a for chunk in await asyncio.gather(*tasks) for a in chunk],
        ]

        def has_keyword(article: TGArticle) -> bool:
            for keyword in keywords:
                if (article.title and keyword in article.title.lower()) or (
                    keyword in article.body.lower()
                ):
                    return True
            return False

        return list(filter(has_keyword, articles))


class TGArticle(Model):

    date: datetime
    title: str | None
    body: str
    url: str
    page: int
    page_url: str
    pages: int

    @classmethod
    async def from_textview(
        cls, url: str, *, page: int, page_url: str, paper: TGPaper, pages: int
    ):
        """
        Constructs a `TGArticle` from a BeautifulSoup instance containing an textview page.

        """
        resp = await paper.http.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        _title = soup.select_one(".haedlinesstory > b:nth-child(1)")
        title = _title.text if _title else None
        body = "\n".join([t.text for t in soup.select(".storyview-div p")])

        return cls(
            date=paper.date,
            title=title,
            body=body,
            url=url,
            page=page,
            page_url=page_url,
            pages=pages,
        )

    def __repr__(self) -> str:
        return f"<TGArticle title={self.title}, body={self.body}, page={self.page}, url={self.url}>"


class TGScraper(BaseScraper[TGArticle]):

    async def scrape(self) -> list[TGArticle]:
        tasks: list[Task[list[TGArticle]]] = []
        TEMP_FIX = (
            ("calcutta", 71),
        )  # FIXME: text view is only available for calcutta for now
        for ed_name, ed_id in TEMP_FIX:
            cur = self.start
            while cur <= self.end:
                paper = TGPaper(ed_name, ed_id, cur, http=self.http)
                tasks.append(asyncio.create_task(paper.search(keywords=self.keywords)))
                cur += timedelta(days=1)
        return [a for chunk in await asyncio.gather(*tasks) for a in chunk]
