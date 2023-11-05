import asyncio
from logging import getLogger
from typing import Annotated, Any
from yarl import URL
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, BeforeValidator
from datetime import datetime

from siren.core import BaseScraper, ScraperProto

logger = getLogger("siren")

class Article(BaseModel):
    url: str
    date: Annotated[
        datetime,
        BeforeValidator(lambda s: datetime.strptime(s, "Published %d.%m.%y, %I:%M %p")),
    ]
    title: str


class SearchResult(BaseModel):
    total: int
    start: int
    end: int
    articles: list[Article]


class Scraper(BaseScraper, ScraperProto):
    BASE_URL = URL("https://www.telegraphindia.com")
    SCRAPER_NAME = "Telegraph Online"

    def parse_page(self, html: str) -> SearchResult:
        soup = BeautifulSoup(html, "html.parser")
        articles: list[Article] = []
        for ul in soup.find_all("ul", class_="storylisting"):
            assert isinstance(ul, Tag)
            for li in ul.find_all("li"):
                assert isinstance(li, Tag)
                article: dict[str, Any] = {}
                # TODO: remove nesting without making linter angry
                if li.a:
                    article["url"] = str(self.BASE_URL) + str(li.a["href"])
                    if div := li.a.div:
                        if div.div:
                            article["date"] = div.div.text
                        if h2 := div.find("h2"):
                            article["title"] = h2.text
                articles.append(Article(**article))
        css = soup.css
        total = start = end = 0
        if css:
            div = css.select_one(".searchresult")
            if div:
                text = div.text.split()
                try:
                    start = int(text[1])
                    end = int(text[3])
                    total = int(text[-1])
                except ValueError:
                    pass
        return SearchResult(total=total, articles=articles, start=start, end=end)

    async def fetch_one(self, keyword: str, page: int) -> SearchResult | None:
        url = self.BASE_URL / "search" % {"page": page, "search-term": keyword}
        logger.info(f"GET {url}")
        resp = await self.client.get(str(url))
        if resp.status_code == 404:
            return None
        return self.parse_page(resp.text)

    async def to_csv(self):
        articles: list[Article] = []
        total: int = 0
        for term in self.keywords:
            initial = await self.fetch_one(term, 0)
            if not initial:
                continue  # Move to next keyword if the first page is empty
            chunks = initial.total // initial.end
            tasks: list[asyncio.Task[SearchResult | None]] = []
            for page in range(1, chunks + 1):
                tasks.append(asyncio.create_task(self.fetch_one(term, page)))
            for fut in asyncio.as_completed(tasks):
                sr = await fut
                if sr:
                    for article in sr.articles:
                        total += 1
                        if self.start <= article.date <= self.end:
                            articles.append(article)
        logger.info(f"{self.SCRAPER_NAME} fetched {total} articles in total. {len(articles)} were selected.")

        return self.models_to_csv(Article, articles)
