from asyncio import Task
import asyncio
from datetime import datetime
from typing import ClassVar, override
from urllib.parse import quote

from pydantic import computed_field
from yarl import URL

from siren.core import BaseScraper, Model, ResultModel

__all__ = ("TheHinduScraper",)

BASE_URL = URL(
    "https://epaper.thehindu.com"
)

PUBLICATIONS = {'th_bangalore': 'Bangalore', 'th_chennai': 'Chennai', 'th_coimbatore': 'Coimbatore', 'th_delhi': 'Delhi', 'th_erode': 'Erode', 'th_hyderabad': 'Hyderabad', 'th_international': 'International', 'th_kochi': 'Kochi', 'th_kolkata': 'Kolkata', 'th_kozhikode': 'Kozhikode', 'th_madurai': 'Madurai', 'th_mangalore': 'Mangalore', 'th_mumbai': 'Mumbai', 'th_thiruvananthapuram': 'Thiruvananthapuram', 'th_visakhapatnam': 'Visakhapatnam', 'th_tiruchirapalli': 'Tiruchirapalli', 'th_vijayawada': 'Vijayawada'}

class TheHinduArticle(ResultModel):

    FIELDS: ClassVar = ["issue_id", "issue_date", "publication_id", "publication_name", "pageno", "url", "keyword", "text"]

    organization_id: str
    publication_name: str
    publication_id: str
    issue_date: datetime
    issue_id: str
    keyword: str
    pageno: str
    articlefilename: str
    CONTENT: list[str]

    @computed_field
    @property
    def text(self) -> str:
        return "\n".join(self.CONTENT)

    @computed_field
    @property
    def url(self) -> str:
        quoted_url = quote(f"{BASE_URL}/ccidist-ws/{self.organization_id}/{self.publication_id}/issues/{self.issue_id}/OPS/{self.articlefilename}", safe="")
        return f"{BASE_URL}/articleshare?articleurl={quoted_url}"

class TheHinduResponseHeader(Model):
    status: int
    QTime: int

class TheHinduResponse(Model):
    numFound: int
    start: int
    numFoundExact: bool
    docs: list[TheHinduArticle]

class TheHinduSearchResult(Model):
    response: TheHinduResponse
    responseHeader: TheHinduResponseHeader

class TheHinduScraper(BaseScraper[TheHinduArticle]):

    CHUNK_SIZE: int = 100

    async def search(self, keyword: str, publication_id: str, rows: int, start: int = 0) -> TheHinduSearchResult | None:
        start_dt = self.start.isoformat()
        end_dt = self.end.isoformat()
        url = str(BASE_URL) + f"/solr/articles/select?fq=os:web&fq=(CONTENT:{keyword} OR articleheadline:{keyword})&fq=organization_id:th&fq=publication_id:{publication_id}&q=issue_date:[{start_dt}Z TO {end_dt}Z]&rows={rows}&start={start}"
        resp = await self.http.get(url)
        if resp.status_code != 200:
            return None
        json = resp.json()
        if "docs" in json["response"]:
            for doc in json["response"]["docs"]:
                doc["keyword"] = keyword
        return TheHinduSearchResult(**json)

    @override
    async def scrape(self) -> list[TheHinduArticle]:
        results: list[TheHinduArticle] = []
        tasks: list[Task[TheHinduSearchResult | None]] = []
        for kw in self.keywords:
            for pid in PUBLICATIONS:
                initial = await self.search(kw, pid, self.CHUNK_SIZE)
                if not initial:
                    continue
                results.extend(initial.response.docs)
                total = initial.response.numFound
                for i in range(1, total // self.CHUNK_SIZE):
                    task = asyncio.create_task(self.search(kw, pid, self.CHUNK_SIZE, start=i*self.CHUNK_SIZE))
                    tasks.append(task)
        for sr in await asyncio.gather(*tasks):
            if sr:
                results.extend(sr.response.docs)

        filtered: list[TheHinduArticle] = []
        for item in results:
            if (
                item.keyword in item.text.lower()
                and not any(kw in item.text.lower() for kw in self.ignore_keywords)
            ):
                filtered.append(item)

        return filtered

