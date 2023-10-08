import asyncio
import csv
from typing import Sequence
from io import StringIO
import aiohttp
from pydantic import BaseModel
from generics.cloud import Cloud, File
from generics.scraper import BaseScraper
from datetime import datetime


EDITIONS = {
    "6539": "The New Indian Express-Kollam",
    "3469": "The New Indian Express-Kozhikode",
    "11447": "The New Indian Express-Kannur",
    "5605": "The New Indian Express-Sambalpur",
    "11782": "The New Indian Express-Jeypore",
    "3359": "The New Indian Express-Bhubaneswar",
    "3353": "The New Indian Express-Chennai",
    "3463": "The New Indian Express-Vishakapatnam",
    "3464": "The New Indian Express-Vijayawada",
    "3381": "The New Indian Express-Hyderabad",
    "3357": "The New Indian Express-Bengaluru",
    "3358": "The New Indian Express-Kochi",
    "3468": "The New Indian Express-Thiruvananthapuram",
    "3361": "The New Indian Express-Madurai",
    "3480": "The New Indian Express-Tirunelveli",
    "3360": "The New Indian Express-Coimbatore",
    "3455": "The New Indian Express-Tiruchy",
    "11449": "The New Indian Express-Nagapattinam",
    "3466": "The New Indian Express-Hubballi",
    "28559": "The New Indian Express-Mysuru",
    "4619": "The New Indian Express-Shivamogga",
    "3456": "The New Indian Express-Vellore",
    "3458": "The New Indian Express-Dharmapuri",
    "8681": "The New Indian Express-Tadepalligudem",
    "8680": "The New Indian Express-Anantapur",
    "5601": "The New Indian Express-Kottayam",
    "3511": "The New Indian Express-Tirupati",
    "11448": "The New Indian Express-Thrissur ",
    "22689": "The New Indian Express-Kalaburagi",
    "3467": "The New Indian Express-Belagavi",
    "3474": "The New Indian Express-Mangaluru",
}


class Article(BaseModel):
    id: str
    pageNum: str
    excerpt: str
    issue_id: str
    title_id: str

    @property
    def name(self):
        return EDITIONS.get(self.title_id, "")

    @property
    def url(self):
        name = "-".join(self.name.split())
        return f"https://epaper.newindianexpress.com/{self.issue_id}/{name}/#page/{self.pageNum}/{self.pageNum}"

    def __str__(self):
        return f"Article-{self.id}-{self.pageNum}-{self.issue_id}-{self.title_id}"


class SearchResult(BaseModel):
    status: bool
    numFound: int | None = None
    start: int | None = None
    to: int | None = None
    data: list[Article] = []


class TNIEScraper(BaseScraper):
    def __init__(
        self, start: datetime, end: datetime, cloud: Cloud, keywords: list[str]
    ):
        self.start = start
        self.end = end
        self.cloud = cloud
        self.keywords = keywords

    async def get_issue_ids(
        self, edition_id: int | str, session: aiohttp.ClientSession
    ):
        url = f"https://epaper.newindianexpress.com/viewer/publishdates/{edition_id}/{int(self.start.timestamp())}/{int(self.end.timestamp())}/json"
        resp = await session.get(url)
        return await resp.json()

    async def get_bulk_issue_ids(
        self, edition_ids: Sequence[int | str], session: aiohttp.ClientSession
    ):
        tasks: list[asyncio.Task[int]] = []
        for eid in edition_ids:
            task = asyncio.create_task(self.get_issue_ids(eid, session))
            tasks.append(task)

        done = await asyncio.gather(*tasks)
        return [i["id"] for x in done for i in x]

    async def _search_issue(
        self, issue_id: str | int, keyword: str, session: aiohttp.ClientSession
    ) -> SearchResult:
        url = f"https://epaper.newindianexpress.com/search/issue/{issue_id}/{keyword}"
        resp = await session.get(url)
        return SearchResult(**await resp.json())

    async def search_issue(
        self, issue_id: str | int, session: aiohttp.ClientSession
    ) -> list[Article]:
        tasks: list[asyncio.Task[SearchResult]] = []
        for term in self.keywords:
            task = asyncio.create_task(self._search_issue(issue_id, term, session))
            tasks.append(task)
        return [
            article
            for sr in await asyncio.gather(*tasks)
            for article in sr.data
            if sr.status
        ]

    async def search_issues(
        self, issue_ids: list[str | int], session: aiohttp.ClientSession
    ) -> list[Article]:
        tasks: list[asyncio.Task[list[Article]]] = []
        for iid in issue_ids:
            task = asyncio.create_task(self.search_issue(iid, session))
            tasks.append(task)
        res = await asyncio.gather(*tasks)
        return [article for chunk in res for article in chunk]

    async def _scrape(self):
        async with aiohttp.ClientSession() as session:
            issue_ids = await self.get_bulk_issue_ids(list(EDITIONS.keys()), session)
            data = await self.search_issues(issue_ids, session)
            headers = list(Article.model_fields) + ["name", "url"]
            f = StringIO()
            writer = csv.writer(f)
            writer.writerow(headers)
            for article in data:
                row = []
                for key in headers:
                    row.append(getattr(article, key, None))
                writer.writerow(row)
            f.seek(0)
            fmt = "%d-%m-%Y"
            return File(
                f.read().encode(),
                f"TNIE_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
            )

    def scrape(self):
        file = asyncio.run(self._scrape())
        self.cloud.upload_file(file, "1cJ39Zh0XDNeVz7whqzofwn9HvtScbI74")
