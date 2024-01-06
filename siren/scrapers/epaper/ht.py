from typing import Any, Annotated, ClassVar
from yarl import URL
from bs4 import BeautifulSoup
from datetime import datetime
import httpx
import asyncio
from siren.core import BaseScraper, Model
from logging import getLogger
from pydantic import Field, BeforeValidator, ValidationError

__all__ = ("HTScraper",)


logger = getLogger("siren")


class HTPartialArticle(Model):
    article_id: str
    page_no: int
    edition_name: str
    edition_date: Annotated[
        datetime, BeforeValidator(lambda raw: datetime.strptime(raw, "%Y/%m/%d"))
    ]
    edition_id: int

    @property
    def url(self):
        return f"https://epaper.hindustantimes.com/Home/ShareArticle?OrgId={self.article_id}&textview=0"


class LinkPicture(Model):
    caption: str
    fullpathlink: str = Field(alias="url")


class Story(Model):
    headlines: list[str] = Field(alias="Headlines")
    body: str = Field(alias="Body")


def _ed_dt_conv(raw: str | None):
    if raw:
        return datetime.strptime(raw, "%d/%m/%Y")


class HTArticle(Model):
    FIELDS: ClassVar = (
        "url",
        "page_number",
        "headline",
        "content",
        "edition_date",
        "edition_name",
        "thumbnail",
    )

    partial: HTPartialArticle
    parent_edition: str | None = Field(alias="ParentEdition", default=None)
    page_id: int | None = Field(alias="PageId", default=None)
    story_id: str | None = Field(alias="storyid", default=None)
    edition_date_: Annotated[datetime | None, BeforeValidator(_ed_dt_conv)] = Field(
        alias="Eddate", default=None
    )
    edition_name_: str | None = Field(alias="Edname", default=None)
    page_number_: str = Field(alias="PageNumber")
    link_pictures: list[LinkPicture] = Field(alias="LinkPicture")
    story_content: list[Story] = Field(alias="StoryContent")

    @classmethod
    async def from_partial(
        cls, partial: HTPartialArticle, *, client: httpx.AsyncClient
    ) -> "HTArticle | None":
        url = f"https://epaper.hindustantimes.com/User/ShowArticleView?OrgId={partial.article_id}"
        resp = await client.get(url)
        json = resp.json()
        try:
            return cls(partial=partial, **json)
        except ValidationError as e:
            logger.error(f"Ignoring exception while validating HTArticle: {e}")

    @property
    def thumbnail(self) -> str | None:
        if p := self.link_pictures:
            return p[0].fullpathlink

    @property
    def page_number(self):
        return self.page_number_ or self.partial.page_no

    @property
    def url(self):
        return self.partial.url

    @property
    def edition_date(self):
        return self.edition_date_ or self.partial.edition_date

    @property
    def edition_name(self):
        return self.edition_name_ or self.partial.edition_name

    @property
    def content(self):
        return self.story_content[0].body

    @property
    def headline(self):
        return self.story_content[0].headlines[0]

    def __hash__(self):
        return hash(self.headline)


class HTScraper(BaseScraper[HTArticle]):
    BASE_URL = URL("https://epaper.hindustantimes.com/Home/Search")
    EDITIONS = list(range(60))

    model = HTArticle

    def build_url(
        self,
        *,
        search_text: str,
        edition_id: int,
        from_date: datetime,
        to_date: datetime,
    ):
        fmt = "%d/%m/%Y"
        return self.BASE_URL % {
            "SearchText": search_text,
            "EditionID": edition_id,
            "FromDate": from_date.strftime(fmt),
            "ToDate": to_date.strftime(fmt),
        }

    async def _scrape_search(
        self,
        *,
        search_text: str,
        edition_id: int,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        client: httpx.AsyncClient,
    ) -> list[HTPartialArticle]:
        from_date = from_date or self.start
        to_date = to_date or self.end
        url = self.build_url(
            search_text=search_text,
            edition_id=edition_id,
            from_date=self.start,
            to_date=self.end,
        )
        resp = await client.get(str(url))
        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[HTPartialArticle] = []
        if css := soup.css:
            for row in css.select(".table > tbody:nth-child(2) > tr"):
                data: dict[str, Any] = {}
                title = row.select_one("td > label")
                assert title is not None, "Could not locate the title label!"
                data["article_id"] = (
                    title.attrs["onclick"].split("','")[1].rstrip("' );")
                )  # TODO: use regex
                aliases = {
                    "PageNo": "page_no",
                    "EditionName": "edition_name",
                    "editionDate": "edition_date",
                }
                for i in range(2, 5):
                    item = row.select_one(f"td:nth-child({i})")
                    assert item is not None
                    data[aliases[item.attrs["data-name"]]] = item.text
                data["edition_id"] = edition_id
                items.append(HTPartialArticle(**data))
        return items

    async def _scrape(
        self,
        *,
        search_text: str,
        edition_id: int,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        client: httpx.AsyncClient,
    ):
        tasks: list[asyncio.Task[HTArticle | None]] = []
        done: set[str] = set()
        for partial in await self._scrape_search(
            search_text=search_text,
            edition_id=edition_id,
            from_date=from_date,
            to_date=to_date,
            client=client,
        ):
            if (aid := partial.article_id) not in done:
                task = asyncio.create_task(
                    HTArticle.from_partial(partial, client=client)
                )
                tasks.append(task)
                done.add(aid)
        return [a for a in await asyncio.gather(*tasks) if a]

    async def scrape(self) -> list[HTArticle]:
        tasks: list[asyncio.Task[list[HTArticle]]] = []
        async with httpx.AsyncClient(timeout=None) as client:
            for ed_id in self.EDITIONS:
                for keyword in self.keywords:
                    task = asyncio.create_task(
                        self._scrape(
                            search_text=keyword, edition_id=ed_id, client=client
                        )
                    )
                    tasks.append(task)
            done: set[str] = set()
            result: list[HTArticle] = []
            for chunk in await asyncio.gather(*tasks):
                for article in chunk:
                    if article.headline not in done:
                        done.add(article.headline)
                        result.append(article)
            return result