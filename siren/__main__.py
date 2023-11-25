import asyncio
import json
import argparse
import logging
from os import getenv
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv
from siren.core import ScraperProto, Local, Drive, File
from siren import SCRAPERS
from httpx import AsyncClient


logger = logging.getLogger("siren")
handler = logging.FileHandler(".log")
handler.setFormatter(logging.Formatter())
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

load_dotenv()


def strptime(string: str):
    return datetime.strptime(string, "%d-%m-%Y").replace(tzinfo=timezone.utc)


parser = argparse.ArgumentParser()
parser.add_argument("scraper", choices=SCRAPERS.keys())
parser.add_argument("--start", default=getenv("START"), type=strptime)
parser.add_argument("--end", default=getenv("END"), type=strptime)
parser.add_argument("--drive")
parser.add_argument("--out", default="data.csv")
parser.add_argument("--keywords", nargs="+", default=["suicide", "kill self"])

args = parser.parse_args()


async def run(Scraper: type[ScraperProto[Any]]) -> File:
    async with AsyncClient() as client:
        scraper = Scraper(
            start=args.start, end=args.end, keywords=args.keywords, http=client
        )
        return await scraper.to_file()


if Scraper := SCRAPERS.get(args.scraper):
    file = asyncio.run(run(Scraper))
    if args.drive:
        cloud = Drive(json.loads(getenv("SERVICE_ACCOUNT_CREDENTIALS", "{}")))
    else:
        cloud = Local(args.out)

    cloud.upload_file(file, args.drive)


else:
    print("That scraper was not found!")
