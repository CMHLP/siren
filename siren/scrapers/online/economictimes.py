from datetime import date
from typing import Self, override
from siren.core import BaseScraper, Model
from bs4 import BeautifulSoup
from yarl import URL

from siren.core.http import HTTP

BASE_URL = URL("https://economictimes.indiatimes.com")


class ETOnlineArticle(Model): ...


class ETOnlineArchive(Model):

    articles: list[ETOnlineArticle]

    @classmethod
    async def get_archive(cls, year: int, month: int, day: int, *, http: HTTP) -> Self:
        starttime = (date(year, month, day) - date(1900, 1, 1)).days + 2
        url = (
            BASE_URL
            / f"archivelist/year-{year},month-{month},starttime-{starttime}.cms"
        )
        resp = await http.get(str(url))
        soup = BeautifulSoup(resp.content)
        article_urls = soup.find("ul", attrs={"class": "content"})
        if article_urls:
            for url in article_urls:
                ...


class ETOnlineScraper(BaseScraper[ETOnlineArticle]):

    @override
    async def scrape(self) -> list[ETOnlineArticle]:
        return await super().scrape()
