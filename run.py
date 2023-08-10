from sys import argv
from datetime import datetime, timedelta
from HindustanTimes.hindustantimes import Scraper

scrapers = {"hindustan_times": Scraper}

print(argv)
target = scrapers.get(argv[1])
if target:
    weeks = 8 if len(argv) == 2 else int(argv[2])
    end = datetime.now()
    start = end - timedelta(weeks=weeks)
    target(start, end).scrape()
else:
    raise ValueError("Invalid scraper!")
