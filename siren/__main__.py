import asyncio
import tomllib
import json
import argparse
import time
import logging
from os import getenv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import traceback
from siren.core import ScraperProto, Local, Drive, File, HTTP
from siren import SCRAPERS
from httpx import Timeout, AsyncClient
from pydantic import BaseModel


logger = logging.getLogger("siren")
load_dotenv()


class Config(BaseModel):
    scraper: str
    keywords: list[str]
    ignore_keywords: list[str]
    start: datetime
    end: datetime
    log_level: int = logging.DEBUG
    log_file: str | None = None
    max_concurrency: int | None = None
    timeout: int | None = None
    cloud: bool = False
    out: str | None = None


def strptime(string: str):
    return datetime.strptime(string, "%Y-%m-%d").replace(tzinfo=timezone.utc)


parser = argparse.ArgumentParser()
parser.add_argument("--scraper")
parser.add_argument("--start", type=strptime)
parser.add_argument("--end", type=strptime)
parser.add_argument("--out", default=None)
parser.add_argument("--keywords", nargs="+", default=[])
parser.add_argument("--ignore-keywords", nargs="+", default=[])
parser.add_argument("--timeout", type=int, default=None)
parser.add_argument("--log-file", default=None)
parser.add_argument("--log-level", type=int, default=logging.DEBUG)
parser.add_argument("--max-concurrency", type=int, default=None)
parser.add_argument("--gen-workflow")
parser.add_argument("--config", default=None)

args = parser.parse_args()

if fp := args.config:
    with open(fp, "rb") as f:
        config = Config(**tomllib.load(f))
else:
    config = Config(**args.__dict__)


logger.setLevel(config.log_level)
if config.log_file:
    handler = logging.FileHandler(config.log_file)
else:
    handler = logging.StreamHandler()
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def upload_file(file: File):
    if config.cloud:
        cloud = Drive(
            json.loads(getenv("SERVICE_ACCOUNT_CREDENTIALS", "{}")),
        )
    else:
        if o := config.out:
            path = Path(o)
        elif s := file.origin:
            path = Path(f"{s.__class__.__name__}-data.csv")
        else:
            path = Path("data.csv")
        cloud = Local(path)

    cloud.upload_file(file, folder=getenv("FOLDER", ""))


async def run_scraper(Scraper: type[ScraperProto[Any]]) -> File | None:
    start = time.perf_counter()
    file = None
    async with AsyncClient(timeout=Timeout(config.timeout)) as client:
        try:
            scraper = Scraper(
                start=config.start,
                end=config.end,
                keywords=config.keywords,
                http=HTTP(client, max_concurrency=config.max_concurrency),
            )
            logger.info(f"Scraping {scraper} with keywords: {config.keywords}")
            file = await scraper.to_file()
        except Exception as e:
            logger.error("\n".join(traceback.format_exception(e)))
    end = time.perf_counter()
    logger.info(f"{Scraper.__name__} completed in {end - start}s.")
    return file


async def run_all():
    tasks: list[asyncio.Task[File | None]] = []
    for _, Scraper in SCRAPERS.items():
        tasks.append(asyncio.create_task(run_scraper(Scraper)))
    for file in asyncio.as_completed(tasks):
        if f := await file:
            upload_file(f)


try:
    import uvloop

    run = uvloop.run
except ModuleNotFoundError:
    import asyncio

    run = asyncio.run

if __name__ == "__main__":
    if Scraper := SCRAPERS.get(config.scraper):
        file = run(run_scraper(Scraper))
        if file:
            upload_file(file)

    elif config.scraper == "all":
        run(run_all())

    else:
        print(
            f"Could not find scraper {config.scraper}! (Please make sure the scraper class is in the __all__ of it's respective module.)"
        )
