from os import getenv, environ
from sys import argv
from datetime import datetime, timedelta
from HindustanTimes.hindustantimes import HTScraper
from Telegraph.monthtitledataframe import TGScraper
from TOI.main import TOIScraper

from dotenv import load_dotenv

import json
from generics.cloud import Drive
from generics.scraper import BaseScraper

load_dotenv()

scrapers: dict[str, type[BaseScraper]] = {
    "hindustan_times": HTScraper,
    "toi": TOIScraper,
    "telegraph": TGScraper,
}


target = scrapers.get(argv[1])


def get_dt(env: str, default: datetime):
    fmt = "%d-%m-%Y"
    if s := getenv(env):
        return datetime.strptime(s, fmt)
    return default


if target:
    end = get_dt("END", datetime.now())
    start = get_dt("START", end - timedelta(weeks=8))
    cloud = Drive(json.loads(environ["SERVICE_ACCOUNT_CREDENTIALS"]))
    target(start, end, cloud).scrape()
else:
    raise ValueError(f"Invalid scraper! Valid options: {', '.join(scrapers)}")
