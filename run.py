from os import getenv, environ
from sys import argv
from datetime import datetime, timedelta
from HindustanTimes.hindustantimes import HTScraper
from Telegraph.monthtitledataframe import TGScraper
from TOI.main import TOIScraper
from newsminute.scraper import NewsMinuteScraper
from readwhere.tnie import TNIEScraper
from readwhere.tribune import TribuneScraper
from dotenv import load_dotenv

import json
from generics.cloud import Cloud, Drive, File
from generics.scraper import BaseScraper

load_dotenv()

scrapers: dict[str, type[BaseScraper]] = {
    "hindustan_times": HTScraper,
    "toi": TOIScraper,
    "telegraph": TGScraper,
    "tnie": TNIEScraper,
    "tribune": TribuneScraper,
    "newsminute": NewsMinuteScraper,
}

keywords = ["suicide", "kill self"]


target = scrapers.get(argv[1])


class MockCloud(Cloud):
    def upload_file(self, file: File, folder: str):
        with open("data.csv", "wb") as f:
            f.write(file.buffer().read())

    def create_folder(self, folder: str, parent: str):
        ...


def get_dt(env: str, default: datetime):
    fmt = "%d-%m-%Y"
    if s := getenv(env):
        return datetime.strptime(s, fmt)
    return default


if target:
    end = get_dt("END", datetime.now())
    start = get_dt("START", end - timedelta(weeks=8))
    cloud = Drive(json.loads(environ["SERVICE_ACCOUNT_CREDENTIALS"]))
    cloud = MockCloud()
    target(start, end, cloud, keywords).scrape()
else:
    raise ValueError(f"Invalid scraper! Valid options: {', '.join(scrapers)}")
