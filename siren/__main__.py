from datetime import datetime, timedelta
import glob
import importlib
import argparse
import logging
import json
from pathlib import Path
import asyncio
from httpx import AsyncClient
from os import getenv, environ
from dotenv import load_dotenv
from siren.core import File, Drive, FileSystem

load_dotenv()
FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger("siren")
logger.setLevel(logging.DEBUG)

async def run_scraper(
    module_path: str, start: datetime, end: datetime, keywords: list[str]
) -> File:
    async with AsyncClient() as client:
        module = importlib.import_module(f"siren.scrapers.{module_path}")
        scraper = module.Scraper(
            start=start,
            end=end,
            keywords=keywords,
            client=client,
        )
        return await scraper.to_csv()


async def run_all(start: datetime, end: datetime, keywords: list[str]):
    tasks: list[asyncio.Task[File]] = []
    async with AsyncClient() as client:
        for file in glob.iglob(f"{__package__}/scrapers/**/*.py", recursive=True):
            path = Path(file)
            dot = ".".join([*path.parts[:-1], path.stem])
            module = importlib.import_module(dot)
            scraper = module.Scraper(
                client=client, start=start, end=end, keywords=keywords
            )
            tasks.append(asyncio.create_task(scraper.to_csv()))
        return await asyncio.gather(*tasks)


def fmt_dt(string: str):
    fmt = "%d-%m-%Y"
    return datetime.strptime(string, fmt)


def get_dt(env: str, default: datetime):
    if s := getenv(env):
        return fmt_dt(s)
    return default


parser = argparse.ArgumentParser(
    prog="SIREN Data Aggregator",
    description="This utility is for running SIREN Scrapers and collecting scraped data.",
)
parser.add_argument("scraper")
parser.add_argument("--start", type=fmt_dt)
parser.add_argument("--end", type=fmt_dt)
parser.add_argument("--keywords", nargs="*")
parser.add_argument("--out", nargs="?")
parser.add_argument("--drive", nargs="?")
args = parser.parse_args()
start = args.start or get_dt("START", datetime.now() - timedelta(weeks=8))
end = args.end or get_dt("END", datetime.now())
keywords = args.keywords or getenv("KEYWORDS", "suicide, kill self").split()


async def main():
    if args.scraper is None:
        files = await run_all(start, end, keywords)
    else:
        files = [await run_scraper(args.scraper, start, end, keywords)]

    cloud = (
        FileSystem(args.out)
        if args.out
        else Drive(json.loads(environ["SERVICE_ACCOUNT_CREDENTIALS"]))
    )
    folder = args.drive or getenv("FOLDER_ID", "")
    for file in files:
        cloud.upload_file(file, folder)


if __name__ == "__main__":
    asyncio.run(main())
