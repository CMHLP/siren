import asyncio
import sys
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


logger = logging.getLogger("siren")
load_dotenv()


def strptime(string: str):
    return datetime.strptime(string, "%d/%m/%Y").replace(tzinfo=timezone.utc)


parser = argparse.ArgumentParser()
parser.add_argument("scraper")
parser.add_argument("--start", default=getenv("START"), type=strptime)
parser.add_argument("--end", default=getenv("END"), type=strptime)
parser.add_argument("--drive", action="store_true")
parser.add_argument("--out", default=None)
parser.add_argument("--keywords", nargs="+", default=None)
parser.add_argument("--timeout", type=int, default=None)
parser.add_argument("--log-file", default=None)
parser.add_argument("--log-level", type=int, default=logging.DEBUG)
parser.add_argument("--max-concurrency", type=int, default=None)
parser.add_argument("--gen-workflow")

args = parser.parse_args()

if args.keywords is None:
    keywords = Path("./keywords.json")
    if not keywords.exists():
        raise RuntimeError(
            "Please supply keywords with the --keywords argument or a JSON file (keywords.json)"
        )
    args.keywords = keywords.read_text()

logger.setLevel(args.log_level)
if args.log_file:
    handler = logging.FileHandler(args.log_file)
else:
    handler = logging.StreamHandler()
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def upload_file(file: File):
    if args.drive:
        cloud = Drive(
            json.loads(getenv("SERVICE_ACCOUNT_CREDENTIALS", "{}")),
        )
    else:
        if o := args.out:
            path = Path(o)
        elif s := file.origin:
            path = Path(f"{s.__class__.__name__}-data.csv")
        else:
            path = Path("data.csv")
        cloud = Local(path)

    cloud.upload_file(file, folder=getenv("FOLDER", ""))


async def run_scraper(Scraper: type[ScraperProto[Any]]) -> File | None:
    start = time.perf_counter()
    async with AsyncClient(timeout=Timeout(args.timeout)) as client:
        try:
            scraper = Scraper(
                start=args.start,
                end=args.end,
                keywords=args.keywords,
                http=HTTP(client, max_concurrency=args.max_concurrency),
            )
            return await scraper.to_file()
        except Exception as e:
            logger.error("\n".join(traceback.format_exception(e)))
    end = time.perf_counter()
    logger.info(f"{Scraper.__name__} completed in {end - start}s.")


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
    if Scraper := SCRAPERS.get(args.scraper):
        if args.gen_workflow:
            with open("template.yml") as f:
                content = f.read().format(
                    scraper=args.scraper, name=Scraper.__name__, args=args.gen_workflow
                )
            with open(f".github/workflows/{Scraper.__name__}.yml", "w") as f:
                f.write(content)
            sys.exit()
        file = run(run_scraper(Scraper))
        if file:
            upload_file(file)

    elif args.scraper == "all":
        run(run_all())

    else:
        print(
            f"Could not find scraper {args.scraper}! (Please make sure the scraper class is in the __all__ of it's respective module.)"
        )
