import asyncio
from datetime import datetime
from typing import ClassVar
from bs4 import BeautifulSoup
import pydantic
from yarl import URL
from siren.core import BaseScraper, Model
from siren.core.http import HTTP

__all__ = ("IndiaTodayOnlineScraper",)
BASE_URL = URL("https://www.indiatoday.in/")


class AuthorItem(Model):
    id: str
    is_inactive_profile: int
    title: str
    image: str
    canonical_url: str
    email: str | None = None


class ContentItem(Model):
    website: str
    domain: str
    lang: str
    title_short: str
    description_short: str
    content_type: str
    rating: str
    is_sponsored: str
    image_small: str
    image_small_alt_text: str
    image_one_to_one: str
    image_three_to_four: str
    share_link_url: str
    canonical_url: str
    amp_url: str
    datetime_updated: datetime
    datetime_published: datetime
    credit: str
    author: list[AuthorItem]
    is_premium: None


class Data(Model):
    title: str
    layout: str
    is_load_more: int
    total_record: int
    content_count_fetched: int
    content_count_display: int
    pagination_cap: int
    datetime_from: str
    datetime_till: str
    is_profile_display: str
    content: list[ContentItem]
    header_html: str


class IndiaTodaySearch(Model):
    status_code: int
    status_message: str
    data: Data
    data_source: str


class IndiaTodayArticle(Model):
    FIELDS: ClassVar[list[str]] = [
        "date",
        "url",
        "title",
        "desc",
        "author",
        "keyword",
        "body",
    ]
    content_item: ContentItem
    body: str
    keyword: str

    @property
    def url(self):
        return str(BASE_URL / self.content_item.canonical_url[1:])

    @property
    def author(self):
        if authors := self.content_item.author:
            return authors[0].title

    @property
    def title(self):
        return self.content_item.title_short

    @property
    def desc(self):
        return self.content_item.description_short

    @property
    def date(self):
        return self.content_item.datetime_published

    @classmethod
    async def from_content_item(
        cls, content_item: ContentItem, *, http: HTTP, keyword: str
    ):
        url = BASE_URL / content_item.canonical_url[1:]
        resp = await http.get(str(url))
        soup = BeautifulSoup(resp.content, "html.parser")
        text: list[str] = []
        if story := soup.select_one("div.Story_description__fq_4S:nth-child(1)"):
            for p in story.find_all("p"):
                text.append(p.text)
        return cls(content_item=content_item, body="\n".join(text), keyword=keyword)


class IndiaTodaySearchFail(Model):
    status_code: int
    status_message: str


class IndiaTodayOnlineScraper(BaseScraper[IndiaTodayArticle]):

    def get_url(self, keyword: str) -> URL:
        fmt = "%Y-%m-%d"
        return (
            BASE_URL
            / "api/ajax/groupsearchlist"
            % {
                "q": keyword,
                "site": "it",
                "ctype": "all,story,video,photo_gallery,audio,visualstory",
                "datestart": self.start.strftime(fmt),
                "dateend": self.end.strftime(fmt),
            }
        )

    async def search(self, keyword: str) -> list[IndiaTodayArticle]:
        url = str(self.get_url(keyword))
        resp = await self.http.get(url)
        try:
            search = IndiaTodaySearch(**resp.json())
        except pydantic.ValidationError:
            return []

        tasks: list[asyncio.Task[IndiaTodayArticle]] = []
        for content in search.data.content:
            task = asyncio.create_task(
                IndiaTodayArticle.from_content_item(
                    content, http=self.http, keyword=keyword
                )
            )
            tasks.append(task)
        return await asyncio.gather(*tasks)

    async def scrape(self) -> list[IndiaTodayArticle]:
        tasks: list[asyncio.Task[list[IndiaTodayArticle]]] = []
        for kw in self.keywords:
            task = asyncio.create_task(self.search(kw))
            tasks.append(task)
        return [article for chunk in await asyncio.gather(*tasks) for article in chunk]
