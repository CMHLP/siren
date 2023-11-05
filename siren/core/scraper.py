import csv
from typing import Protocol, TypeVar
from datetime import datetime

from httpx import AsyncClient
from pydantic import BaseModel

from io import StringIO

from .file import File


class ScraperProto(Protocol):
    start: datetime
    end: datetime
    keywords: list[str]
    SCRAPER_NAME: str

    async def to_csv(self) -> File:
        ...


T = TypeVar("T", bound=BaseModel)

class BaseScraper:

    SCRAPER_NAME: str

    def __init__(
        self,
        *,
        start: datetime,
        end: datetime,
        keywords: list[str],
        client: AsyncClient
    ):
        self.start = start
        self.end = end
        self.keywords = keywords
        self.client = client


    def models_to_csv(self, model: type[T], data: list[T]) -> File:
        file = StringIO()
        writer = csv.writer(file)
        headers = list(model.model_fields)
        writer.writerow(headers)
        for article in data:
            row: list[str | None] = []
            for key in headers:
                row.append(getattr(article, key, None))
            writer.writerow(row)
        file.seek(0)
        fmt = "%d-%m-%Y"
        return File(
            file.read().encode(),
            f"{self.SCRAPER_NAME}_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
        )
