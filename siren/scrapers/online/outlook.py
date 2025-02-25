import asyncio
import re
from asyncio import Task
from datetime import datetime
from json import JSONDecodeError
from typing import Any, ClassVar, override

from pydantic import Field, ValidationError, computed_field
from yarl import URL

from siren.core import BaseScraper, Model, ResultModel

__all__ = ("OutlookOnlineScraper",)

BASE_URL = URL("https://www.outlookindia.com/api/v1/advanced-search")


class OutlookStoryElements(Model):
    type: str
    text: str = ""


class OutlookCard(Model):
    story_elements: list[OutlookStoryElements] = Field(alias="story-elements")

    @computed_field
    @property
    def text(self) -> str:
        return re.sub(r"<.*?>", "", "\n".join(st.text for st in self.story_elements))


class OutlookArticle(ResultModel):

    FIELDS: ClassVar = ("author_name", "keyword", "date", "url", "text")

    author_name: str = Field(alias="author-name")
    headline: str
    cards: list[OutlookCard]
    keyword: str
    url: str
    date: datetime = Field(alias="published-at")

    @computed_field
    @property
    def text(self) -> str:
        return "\n".join(c.text for c in self.cards)


class OutlookSearchResult(Model):

    def __init__(self, **data: Any):
        if "items" in data:
            for item in data["items"]:
                item["keyword"] = data[
                    "keyword"
                ]  # inject the keyword into the article here, TODO: write a cleaner abstraction for this
        super().__init__(**data)

    total: int
    items: list[OutlookArticle]
    keyword: str


class OutlookOnlineScraper(BaseScraper[OutlookArticle]):

    CHUNK_SIZE = 100

    async def get_page(
        self, q: str, limit: int, offset: int
    ) -> OutlookSearchResult | None:
        url = BASE_URL % {"q": q, "limit": limit, "offset": offset}
        resp = await self.http.get(str(url))
        try:
            return OutlookSearchResult(keyword=q, **resp.json())
        except (ValidationError, JSONDecodeError):
            return None

    @override
    async def scrape(self) -> list[OutlookArticle]:
        items: list[OutlookArticle] = []
        for keyword in self.keywords:
            initial = await self.get_page(keyword, self.CHUNK_SIZE, 0)
            if not initial:
                continue
            total = initial.total
            items.extend(initial.items)
            tasks: list[Task[OutlookSearchResult | None]] = []
            for i in range(1, (total // self.CHUNK_SIZE)):
                task = asyncio.create_task(
                    self.get_page(keyword, self.CHUNK_SIZE, self.CHUNK_SIZE * i)
                )
                tasks.append(task)
            for result in await asyncio.gather(*tasks):
                if result:
                    items.extend(result.items)
        filtered: list[OutlookArticle] = []
        for item in items:
            if (
                item.keyword in item.text.lower()
                and self.start <= item.date.replace(tzinfo=None) <= self.end
                and not any(kw in item.text.lower() for kw in self.ignore_keywords)
            ):
                filtered.append(item)

        return filtered
