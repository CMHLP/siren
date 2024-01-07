import asyncio
import json
import argparse
import logging
from os import getenv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import traceback
from siren.core import ScraperProto, Local, Drive, File
from siren import SCRAPERS
from httpx import AsyncClient, Timeout


logger = logging.getLogger("siren")
handler = logging.FileHandler(".log")
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

load_dotenv()


def strptime(string: str):
    return datetime.strptime(string, "%d-%m-%Y").replace(tzinfo=timezone.utc)


parser = argparse.ArgumentParser()
parser.add_argument("scraper")
parser.add_argument("--start", default=getenv("START"), type=strptime)
parser.add_argument("--end", default=getenv("END"), type=strptime)
parser.add_argument("--drive")
parser.add_argument("--out", default="data.csv")
parser.add_argument("--keywords", nargs="+", default=["suicide", "kill self"])
parser.add_argument("--timeout", type=int, default=None)

args = parser.parse_args()


def upload_file(file: File):
    if args.drive:
        cloud = Drive(json.loads(getenv("SERVICE_ACCOUNT_CREDENTIALS", "{}")))
    else:
        path = Path(args.out)
        if s := file.origin:
            path = path.parent / f"{s.__class__.__name__}-{path.name}"
        cloud = Local(path)

    cloud.upload_file(file, args.drive)


async def run(Scraper: type[ScraperProto[Any]]) -> File | None:
    async with AsyncClient(timeout=Timeout(args.timeout)) as client:
        try:
            scraper = Scraper(
                start=args.start, end=args.end, keywords=args.keywords, http=client
            )
            return await scraper.to_file()
        except Exception as e:
            logger.error("\n".join(traceback.format_exception(e)))


async def run_all():
    tasks: list[asyncio.Task[File | None]] = []
    for _, Scraper in SCRAPERS.items():
        tasks.append(asyncio.create_task(run(Scraper)))
    for file in asyncio.as_completed(tasks):
        if f := await file:
            upload_file(f)


if Scraper := SCRAPERS.get(args.scraper):
    file = asyncio.run(run(Scraper))
    if file:
        upload_file(file)


elif args.scraper == "all":
    asyncio.run(run_all())

else:
    print(
        f"Could not find scraper {args.scraper}! (Please make sure the scraper class is in the __all__ of it's respective module.)"
    )
