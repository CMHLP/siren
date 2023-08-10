from os import getenv
from sys import argv
from datetime import datetime, timedelta
from HindustanTimes.hindustantimes import Scraper

scrapers = {"hindustan_times": Scraper}
target = scrapers.get(argv[1])


def get_dt(env: str, default: datetime):
    fmt = "%d-%m-%Y"
    if s := getenv(env):
        return datetime.strptime(s, fmt)
    return default


if target:
    end = get_dt("END", datetime.now())
    start = get_dt("START", end - timedelta(weeks=8))
    target(start, end).scrape()
else:
    raise ValueError("Invalid scraper!")
