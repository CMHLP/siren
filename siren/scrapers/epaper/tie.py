from datetime import datetime, timedelta

from pydantic import Field, ValidationError
from siren.core import BaseScraper, Model
from yarl import URL
from logging import getLogger

import asyncio

logger = getLogger("siren")


__all__ = ("TIEScraper",)

PRODUCTS = {
    "Lucknow": 4282,
    "Ahmedabad": 4294,
    "Pune": 4279,
    "Mumbai": 4276,
    "Delhi": 4273,
    "EYE": 5881,
    "LOCKDOWN SPECIAL": 5882,
    "Chandigarh": 4285,
    "Kolkata": 4291,
    "Jaipur": 4288,
}

HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiI1ZjNjYzYyNDQ2ZGQ2YjNlOWI1ZTc2YjgiLCJleHAiOjE3MDQ5MDEyNzUsImlhdCI6MTcwNDgxNDg3NSwiVXNlci1BZ2VudCI6Ik1vemlsbGEvNS4wIChYMTE7IExpbnV4IHg4Nl82NDsgcnY6MTIyLjApIEdlY2tvLzIwMTAwMTAxIEZpcmVmb3gvMTIyLjAiLCJwZXJtaXNzaW9ucyI6IltdIn0.YP6aXhqtdLCocAfvsbZzWwddhS6yJczqR1SDOMjUEUV2DGtYRCOJn-0AUHMisih768nx74jZxsXD6LaJNrMR4Q"
}


class TIEMonthSearchProduct(Model):
    id: int


class TIEMonthSearchArticle(Model):
    id: int
    product: TIEMonthSearchProduct
    name: str
    publish_date: datetime = Field(alias="publishDate")
    description: str
    issue_id: str = Field(alias="issueId")


class TIEMonthSearch(Model):
    count: int
    results: list[TIEMonthSearchArticle] = []


class TIESearchItem(Model):
    id: str
    pageNum: str
    excerpt: str
    issue_id: str
    title_id: str


class TIEArticle(Model):
    id: str
    page_num: str
    excerpt: str
    name: str
    publish_date: datetime
    edition: str | None = None
    url: str | None = None


class TIESearch(Model):
    status: bool
    numFound: int | None = None
    data: list[TIESearchItem] = []


class TIEScraper(BaseScraper[TIEArticle]):
    model = TIEArticle

    async def search(self, issue_id: str, keyword: str) -> TIESearch | None:
        url = URL(
            f"https://epaper.indianexpress.com/search/issue/{issue_id}/{keyword}/1"
        )
        resp = await self.http.get(str(url))
        try:
            return TIESearch(**resp.json())
        except ValidationError as e:
            logger.error(f"Ignoring exception {e} while validating TIESearch.")

    async def get_month(
        self, product_id: int, month: int, year: int
    ) -> TIEMonthSearch | None:
        url = URL(
            f"https://ecommerce.indianexpress.com/api/partner-delivery-data/?productId={product_id}&month={month}&year={year}&size=31"
        )
        resp = await self.http.get(str(url), headers=HEADERS)
        results = resp.json()
        try:
            return TIEMonthSearch(**results)
        except ValidationError as e:
            logger.error(f"Ignoring exception {e} while validating TIEMonthSearch.")

    async def scrape_product(self, product_id: int) -> list[TIEArticle]:
        cur = self.start
        month_tasks: list[asyncio.Task[TIEMonthSearch | None]] = []
        while cur <= self.end:
            task = asyncio.create_task(
                self.get_month(product_id, month=cur.month, year=cur.year)
            )
            month_tasks.append(task)
            if (m := cur.month + 1) <= 12:
                cur = cur.replace(month=m)
            else:
                cur = cur.replace(month=1, year=cur.year + 1)
        articles: dict[str, TIEMonthSearchArticle] = {}
        search_tasks: list[asyncio.Task[TIESearch | None]] = []
        for task in asyncio.as_completed(month_tasks):
            if search := await task:
                for article in search.results:
                    articles[article.issue_id] = article
                    for keyword in self.keywords:
                        search_tasks.append(
                            asyncio.create_task(self.search(article.issue_id, keyword))
                        )

        results: list[TIEArticle] = []
        for task in asyncio.as_completed(search_tasks):
            if search := await task:
                for item in search.data:
                    month_article = articles[item.issue_id]
                    results.append(
                        TIEArticle(
                            id=item.issue_id,
                            page_num=item.pageNum,
                            excerpt=item.excerpt.replace("<strong>", "").replace(
                                "</strong>", ""
                            ),
                            name=month_article.name,
                            publish_date=month_article.publish_date
                            + timedelta(
                                days=1
                            ),  # for some reason the publish date is a day behind
                        )
                    )
        return results

    async def scrape(self) -> list[TIEArticle]:
        results: list[TIEArticle] = []
        for edition, product_id in PRODUCTS.items():
            for article in await self.scrape_product(product_id):
                article.edition = edition
                fmt = "%B-%d-%Y"
                article.url = f"https://epaper.indianexpress.com/{article.id}/{edition}/{article.publish_date.strftime(fmt)}#page/{article.page_num}/1"
                results.append(article)
        return results
