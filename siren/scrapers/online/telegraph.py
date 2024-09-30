from asyncio import Task
import asyncio
from datetime import datetime
import re
from bs4 import BeautifulSoup, Tag
from yarl import URL
from siren.core import Model, BaseScraper
from siren.core.http import HTTP
import logging

logger = logging.getLogger(__name__)
__all__ = ("TelegraphOnlineScraper",)

BASE_URL = URL("https://www.telegraphindia.com/")
HEADERS = {
    "Host": "www.telegraphindia.com",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.telegraphindia.com/",
    "Connection": "keep-alive",
    "Cookie": "AKA_A2=A",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i",
    "TE": "trailers",
}


class TGOnlineSearchPage(Model):
    total: int
    article_urls: list[str]

    async def filter(
        self, start: datetime, end: datetime, *, http: HTTP
    ) -> list["TelegraphOnlineArticle"]:
        tasks: list[Task[TelegraphOnlineArticle]] = []
        for url in self.article_urls:
            task = asyncio.create_task(TelegraphOnlineArticle.from_url(url, http=http))
            tasks.append(task)
        articles: list[TelegraphOnlineArticle] = []
        for fut in asyncio.as_completed(tasks):
            article = await fut
            if article.date and start < article.date < end:
                articles.append(article)
        logger.info(
            f"Filtered {len(articles)} articles from {len(self.article_urls)} articles!"
        )
        return articles


class TelegraphOnlineArticle(Model):
    date: datetime | None
    title: str
    content: str
    author: str
    location: str
    header: str

    @classmethod
    async def from_url(cls, url: str, *, http: HTTP):
        resp = await http.get(str(BASE_URL / url), headers=HEADERS)

        def parse():
            soup = BeautifulSoup(resp.content, "html.parser")
            title = header = author = location = ""
            date = None
            if articlet := soup.select_one(".articletsection"):
                title = tag.text if (tag := articlet.find("h1")) else ""
                header = tag.text if (tag := articlet.find("h2")) else ""
                if meta := articlet.select_one(".publishdate"):
                    author = getattr(meta.find("strong"), "text", str())
                    location = getattr(meta.find("span"), "text", str())
                    if match := re.search(
                        r"Published (\d{2}\.\d{2}\.\d{2}), (\d{2}:\d{2}) (\w{2})",
                        meta.text,
                    ):
                        date = datetime.strptime(match.group(1), "%d.%m.%y")
            if paragraphs := soup.select_one("#contentbox > div"):
                content: list[str] = []
                for p in paragraphs.find_all("p"):
                    content.append(p.text)
                body = "\n".join(content)
            else:
                body = ""

            return cls(
                date=date,
                title=title,
                header=header,
                content=body,
                author=author,
                location=location,
            )

        return await asyncio.to_thread(parse)


class TelegraphOnlineScraper(BaseScraper[TelegraphOnlineArticle]):

    def get_url(self, keyword: str, page: int) -> URL:
        return (BASE_URL / "search") % {"search-term": keyword, "page": page}

    async def search_all(self, keyword: str) -> list[TelegraphOnlineArticle]:
        PAGE_SIZE = 20
        if initial := await self.search_page(keyword):
            tasks: list[Task[TGOnlineSearchPage | None]] = []
            pages = initial.total // PAGE_SIZE
            logger.info(f"Found {pages} pages for {keyword}")
            for page in range(1, pages + 1):
                tasks.append(asyncio.create_task(self.search_page(keyword, page=page)))

            articles: list[TelegraphOnlineArticle] = await initial.filter(
                self.start, self.end, http=self.http
            )
            for fut in asyncio.as_completed(tasks):
                search_page = await fut
                if search_page:
                    articles.extend(
                        await search_page.filter(self.start, self.end, http=self.http)
                    )
            return articles
        else:
            articles: list[TelegraphOnlineArticle] = []
            return articles

    async def search_page(
        self, keyword: str, *, page: int = 0
    ) -> TGOnlineSearchPage | None:
        url = self.get_url(keyword, page)
        resp = await self.http.get(str(url), headers=HEADERS)

        def parse():
            soup = BeautifulSoup(resp.content, "html.parser")
            article_urls: list[str] = []
            if results := soup.find("div", class_="searchresult"):
                total = int(results.text.split()[-1])
                if storylisting := soup.find("ul", class_="storylisting"):
                    for anchor in storylisting.select("li > a"):
                        href = anchor.get("href")[1:]
                        article_urls.append(href)
                return TGOnlineSearchPage(total=total, article_urls=article_urls)
            else:
                return None

        return await asyncio.to_thread(parse)

    async def scrape(self) -> list[TelegraphOnlineArticle]:
        tasks: list[Task[list[TelegraphOnlineArticle]]] = []
        for kw in self.keywords:
            task = asyncio.create_task(self.search_all(kw))
            tasks.append(task)
        return [article for chunk in await asyncio.gather(*tasks) for article in chunk]
