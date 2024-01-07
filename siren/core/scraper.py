from abc import abstractmethod, ABC
import csv
from datetime import datetime
from io import StringIO
from .http import ClientProto
from .model import Model
from .file import File
from typing import Any, Protocol


class ScraperProto[T: Model](Protocol):
    """
    Scraper Protocol class. All scrapers should adhere to this protocol.

    Attributes
    ----------

    start: :class:`datetime`
        The earliest datetime to include.

    end: :class:`datetime`
        The latest datetime to include.

    model: :class:type[`Model`]
        The Model that represents a unit of scraped data (such as an Article)

    """

    start: datetime
    end: datetime
    keywords: list[str]
    model: type[T]
    http: ClientProto

    def __init__(
        self,
        *,
        start: datetime,
        end: datetime,
        keywords: list[str],
        http: ClientProto,
    ):
        ...

    @abstractmethod
    async def scrape(self) -> list[T]:
        ...

    @abstractmethod
    async def to_file(self) -> File:
        ...


class BaseScraper[T: Model](ABC, ScraperProto[T]):
    model: type[T]

    def __init__(
        self,
        *,
        start: datetime,
        end: datetime,
        keywords: list[str],
        http: ClientProto,
    ):
        self.start = start
        self.end = end
        self.keywords = keywords
        self.http = http

    @abstractmethod
    async def scrape(self) -> list[T]:
        raise NotImplementedError

    async def to_csv(
        self,
        *,
        include: set[str] = set(),
        exclude: set[str] = set(),
        aliases: dict[str, str] = {},
    ) -> StringIO:
        """
        Return a CSV-formatted StringIO of the scraped data.

        Parameters
        ----------

        include: :class:`set[str]`
            Extra attributes to include. Defaults to an empty set.

        exclude: :class:`set[str]`
            Attributes to exclude. Defaults to an empty set.

        aliases: :class:`dict[str, str]`
            A dictionary that maps attributes to their aliases for the headers. Defaults to an empty dict.

        Returns
        -------

        :class:`io.StringIO`
            A StringIO object.


        """

        data = await self.scrape()
        file = StringIO()
        fields = set(self.model.model_fields)
        fields |= include
        fields -= exclude
        fields = getattr(self.model, "FIELDS", None) or fields
        headers = [aliases.get(f, f) for f in fields]
        writer = csv.writer(file)
        writer.writerow(headers)

        for article in data:
            row: list[Any] = []
            for field in fields:
                row.append(getattr(article, field, "- no data -"))
            writer.writerow(row)

        file.seek(0)
        return file

    async def to_file(self) -> File:
        file = await self.to_csv()
        fmt = "%d-%m-%Y"
        return File(
            file.read().encode(),
            f"{self.__class__.__name__}_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
            origin=self
        )
