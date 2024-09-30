from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from .core import BaseReadwhereScraper, PartialArticle
from datetime import datetime
from siren.core import Model, ClientProto
from typing import ClassVar, Self, no_type_check
from PIL import Image, ImageOps
from io import BytesIO
import asyncio
import logging
import pytesseract  # pyright: ignore[reportMissingTypeStubs]


# import easyocr

logger = logging.getLogger(__name__)
# reader = easyocr.Reader(["en"])


class PageChunk(Model):
    tx: int
    ty: int
    width: int
    height: int
    url: str

    async def search(
        self, *, client: ClientProto, keywords: list[str]
    ) -> tuple[Self, str]:
        """Return a list of strings found from the keywords list"""
        resp = await client.get(self.url)
        buf = BytesIO(resp.content)
        image = Image.open(buf).convert(
            "RGBA"
        )  # pyright: ignore[reportUnknownMemberType]
        image = ImageOps.grayscale(image)
        logger.info(f"Running OCR on {image.width}*{image.height} chunk: {self.url}")
        try:
            text: str = await asyncio.to_thread(pytesseract.image_to_string, image)
            # buffer = BytesIO()
            # image.save(buffer, format="jpeg")
            # buffer.seek(0)
            # raw = await asyncio.to_thread(reader.readtext, buffer.read(), detail=0)
            # text: str = " ".join(raw)
        except (pytesseract.TesseractError, RuntimeError) as e:
            logger.error(
                f"Ignoring exception while extracting text from {self.url}: {e}"
            )
            text = ""
        # split = text.lower().split()
        # items: list[str] = split
        # # for kw in keywords:
        # #     for word in split:
        # #         if kw == word:
        # #             items.append(word)
        return self, text


class PageLevel(Model):
    width: int
    height: int
    chunks: list[PageChunk]


class Levels(Model):
    thumbs: PageLevel
    level0: PageLevel
    leveldefault: PageLevel
    level1: PageLevel
    level2: PageLevel
    header: PageLevel


class Page(Model):
    key: str
    pagenum: int
    levels: Levels

    async def search(self, *, keywords: list[str], client: ClientProto) -> PageResult:
        """Return a `PageResult` containing self (the page in which matches were found) and a mapping of url to a list of the matches found in the corresponding image."""
        target = self.levels.level2
        matches: dict[str, str] = {}
        tasks: list[asyncio.Task[tuple[PageChunk, str]]] = []
        for chunk in target.chunks:
            task = asyncio.create_task(chunk.search(keywords=keywords, client=client))
            tasks.append(task)
        for fut in asyncio.as_completed(tasks):
            chunk, found = await fut
            if found:
                matches[chunk.url] = found
        return PageResult(page=self, matches=matches)


class PageResult(Model):
    page: Page
    matches: dict[str, str]


class PageMeta(Model):
    pages: dict[str, Page]

    async def search(
        self, *, keywords: list[str], client: ClientProto
    ) -> list[PageResult]:
        tasks: list[asyncio.Task[PageResult]] = []
        for _page_number, page in self.pages.items():
            tasks.append(
                asyncio.create_task(page.search(keywords=keywords, client=client))
            )
        return await asyncio.gather(*tasks)


class Result(Model):
    pages: list[PageResult]
    partial: PartialArticle

    FIELDS: ClassVar = ["url", "date", "edition", "text"]

    @property
    def date(self):
        return self.partial.published

    @property
    def edition(self):
        return self.partial.edition_name

    @property
    def url(self):
        return self.partial.url

    @property
    def text(self):
        return [page.matches for page in self.pages]


class PartialArticleOCR:
    def __init__(self, partial: PartialArticle):
        self.partial = partial

    async def get_pagemeta(self, *, client: ClientProto) -> PageMeta:
        partial = self.partial
        url = partial.base_url / f"pagemeta/get/{partial.id}/1-50"
        url %= {
            "type": "newspaper",
            "user": "2341985",
            "crypt": "313581a5b8d413a08e027161b18e2921857250ef",
            "key": "1711454980",
        }
        # TODO: Can we find a way around using these constants?
        resp = await client.get(str(url))
        return PageMeta(pages=resp.json())

    async def search(self, client: ClientProto, keywords: list[str]):
        meta = await self.get_pagemeta(client=client)
        pages = await meta.search(keywords=keywords, client=client)
        return Result(pages=pages, partial=self.partial)


class BaseReadwhereScraperOCR(BaseReadwhereScraper):

    async def get_partial_articles_ocr(
        self,
        edition_id: int | str,
        edition_name: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PartialArticleOCR]:
        return [
            PartialArticleOCR(p)
            for p in await super().get_partial_articles(
                edition_id, edition_name, start, end
            )
        ]

    async def search_edition_ocr(
        self, edition_id: int | str, edition_name: str
    ) -> list[Result]:
        logger.info(f"Scraping edition {edition_name}!")
        partials = await self.get_partial_articles_ocr(edition_id, edition_name)
        tasks: list[asyncio.Task[Result]] = []
        for partial in partials:
            task = asyncio.create_task(
                partial.search(client=self.http, keywords=self.keywords)
            )
            tasks.append(task)
            break  # TODO: remove after benchmarking
        return await asyncio.gather(*tasks)

    @no_type_check
    async def scrape(self) -> list[Result]:
        with ThreadPoolExecutor(max_workers=1) as pool:
            asyncio.get_event_loop().set_default_executor(pool)
            tasks: list[asyncio.Task[list[Result]]] = []
            for edition_id, edition_name in self.EDITIONS.items():
                task = asyncio.create_task(
                    self.search_edition_ocr(edition_id, edition_name)
                )
                tasks.append(task)
                break  # TODO: remove after benchmarking
            data = [
                article for chunk in await asyncio.gather(*tasks) for article in chunk
            ]
            return data

    async def to_csv(
        self,
        *,
        include: set[str] = set(),
        exclude: set[str] = set(),
        aliases: dict[str, str] = {},
    ):
        include.add("url")
        exclude.add("base_url")
        return await super().to_csv(include=include, exclude=exclude, aliases=aliases)
