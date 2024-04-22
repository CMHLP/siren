import asyncio
from datetime import datetime, timedelta
from io import BytesIO
import sys
import re
from time import perf_counter
from PIL import Image
import pytesseract
from playwright.async_api import Browser, async_playwright
import logging
from yarl import URL
from siren.core import BaseScraper, Model


__all__ = ("TGScraper",)

logger = logging.getLogger(__name__)


EDITIONS = {"calcutta": 71, "north bengal": 72, "south bengal": 73}


class TGArticle(Model):
    page: int
    date: datetime
    body: str
    edition: str
    url: str


class TGPage(Model):
    articles: list[str]
    number: int
    date: datetime
    edition: str
    url: str
    pages: int


class TGScraper(BaseScraper[TGArticle]):

    BASE_URL = URL("https://epaper.telegraphindia.com/")

    IMAGE_REGEX = re.compile(r"\('(\d+)','(\d+)','(\d+)'\)")

    async def scrape(self) -> list[TGArticle]:
        async with async_playwright() as pw:
            firefox = pw.firefox
            browser = await firefox.launch(headless=True)
            cur = self.start
            tasks: list[asyncio.Task[list[TGPage]]] = []
            while cur < self.end:
                for edition in EDITIONS:
                    task = asyncio.create_task(
                        self.search_paper(edition, cur, browser=browser)
                    )
                    tasks.append(task)
                cur += timedelta(days=1)
            articles: list[TGArticle] = []
            chunks = await asyncio.gather(*tasks)
            for chunk in chunks:
                for page in chunk:
                    for text in page.articles:
                        articles.append(
                            TGArticle(
                                page=page.number,
                                date=page.date,
                                body=text,
                                edition=page.edition,
                                url=page.url,
                            )
                        )
            return articles

    async def scan_image(self, url: str) -> str | None:
        resp = await self.http.get(url)
        data = resp.content

        def _thread() -> str:
            image = Image.open(BytesIO(data))
            image.save(f"sample.jpg")
            return pytesseract.image_to_string(image, lang="eng")

        text = await asyncio.to_thread(_thread)
        return text

    async def search_paper(
        self, edition: str, date: datetime, *, browser: Browser
    ) -> list[TGPage]:
        logger.info(f"Searching EPaper {edition} {date}")
        initial = await self.fetch_page(
            edition=edition, page_num=1, date=date, browser=browser
        )
        if not initial:
            return []
        tasks: list[asyncio.Task[TGPage | None]] = []
        for i in range(2, initial.pages + 1):
            task = asyncio.create_task(
                self.fetch_page(edition=edition, date=date, page_num=i, browser=browser)
            )
            tasks.append(task)
            await task  # NOTE: remove to increase concurrency

        results = [initial, *await asyncio.gather(*tasks)]
        return [page for page in results if page and page.articles]

    async def fetch_page(
        self, edition: str, date: datetime, page_num: int, *, browser: Browser
    ) -> TGPage | None:
        url = (
            self.BASE_URL
            / edition
            / date.strftime("%Y-%m-%d")
            / str(EDITIONS[edition])
            / f"Page-{page_num}.html"
        )
        page = await browser.new_page()
        try:
            await page.goto(str(url), timeout=120000, wait_until="domcontentloaded")
        except Exception as e:
            logger.error(f"Ignoring exception {e}\n-> Page: {url}")
            return None
        loc = await page.locator(
            "#outdivd1 > map:nth-child(2) > map:nth-child(1) > *"
        ).all()
        tasks: list[asyncio.Task[str | None]] = []
        start = perf_counter()
        for mapping in loc:
            if event := await mapping.get_attribute("onclick"):
                if m := self.IMAGE_REGEX.search(event):
                    url = (
                        self.BASE_URL
                        / "epaperimages"
                        / date.strftime("%d%m%Y")
                        / f"{m.group(2)}.jpg"
                    )
                    task = asyncio.create_task(self.scan_image(str(url)))
                    tasks.append(task)
                else:
                    logger.error(f"Could not find IDs in mapping!")
            else:
                logger.error("No mappings found!")
        matches = list(filter(None, await asyncio.gather(*tasks)))
        logger.info(
            f"Finished OCR for {edition} {page_num} in {perf_counter() - start}s ({len(tasks)} tasks)"
        )
        pages_tag = await page.locator(
            ".countR1 > span:nth-child(3) > b:nth-child(1)"
        ).first.text_content()
        pages = int(pages_tag) if pages_tag else 0
        await page.close()
        return TGPage(
            articles=matches,
            number=page_num,
            date=date,
            edition=edition,
            url=str(url),
            pages=pages,
        )
