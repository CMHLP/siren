import asyncio
import tomllib
import json
import argparse
import time
import logging
from os import getenv
from datetime import datetime, timezone, timedelta
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


class Cloud(BaseModel):
    enabled: bool = False
    root_folder_id: str


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
    cloud: Cloud | None = None
    out: str | None = None


def strptime(string: str):
    return datetime.strptime(string, "%Y-%m-%d").replace(tzinfo=timezone.utc)


parser = argparse.ArgumentParser()
parser.add_argument("--scraper")
parser.add_argument("--start", type=strptime, default=None)
parser.add_argument("--end", type=strptime, default=None)
parser.add_argument("--out", default=None)
parser.add_argument("--keywords", nargs="+", default=[])
parser.add_argument("--ignore-keywords", nargs="+", default=[])
parser.add_argument("--timeout", type=int, default=None)
parser.add_argument("--log-file", default=None)
parser.add_argument("--log-level", type=int, default=logging.DEBUG)
parser.add_argument("--max-concurrency", type=int, default=None)
parser.add_argument("--gen-workflow")
parser.add_argument("--config", default=None)
parser.add_argument("--days", type=int, default=1)
parser.add_argument("--cloud", action="store_true")
parser.add_argument("--root_folder_id", default=None)

args = parser.parse_args()


if fp := args.config:
    with open(fp, "rb") as f:
        config = Config(**tomllib.load(f))
else:

    if not any((args.start, args.end)):
        args.start = datetime.now()
        args.end = datetime.now() + timedelta(days=args.days)
    elif args.start:
        args.end = args.start + timedelta(days=args.days)
    else:
        args.start = args.end - timedelta(days=args.days)

    if args.cloud:
        assert isinstance(
            args.root_folder_id, str
        ), "--root_folder_id must be passed along with --cloud!"

        args.cloud = {"enabled": True, "root_folder_id": args.root_folder_id}
    else:
        args.cloud = None

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

if config.cloud and config.cloud.enabled:
    cloud = Drive(
        json.loads(getenv("SERVICE_ACCOUNT_CREDENTIALS", "{}")),
        root=config.cloud.root_folder_id,
    )
else:
    cloud = Local(Path("."))


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
            cloud.upload(f)


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
            cloud.upload(file)

    elif config.scraper == "all":
        run(run_all())

    else:
        print(
            f"Could not find scraper {config.scraper}! (Please make sure the scraper class is in the __all__ of it's respective module.)"
        )
