from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO
import json
import os
import re
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from yarl import URL

from generics.cloud import Drive, File
from generics.scraper import BaseScraper


class Scraper(BaseScraper):
    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end
        self.items = []

        chrome_driver_path = (
            os.environ.get("CHROMEDRIVER_PATH") or "chromedriver.exe"
        )  # default to chromedriver.exe if env var missing

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        self.base_url = URL(
            "https://epaper.hindustantimes.com/Home/Search?SearchText=suicide&EditionId={}&grid-column=editionDate&grid-dir=0&grid-page={}"
        )
        service = Service(executable_path=chrome_driver_path)
        self.browser = webdriver.Chrome(service=service, options=chrome_options)
        self.browser.set_page_load_timeout(60)
        self.cloud = Drive(creds=json.loads(os.environ["SERVICE_ACCOUNT_CREDENTIALS"]))

    def scrape_one(self, ed_id, page_num):
        try:
            fmt = "%d/%m/%Y"
            dates = {
                "FromDate": self.start.strftime(fmt),
                "ToDate": self.end.strftime(fmt),
            }
            url = self.base_url % dates
            url = str(url).format(ed_id, page_num)
            response = requests.get(url)

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all("tr", {"class": "grid-row"})

            for row in rows:
                label = row.find("label", {"onclick": True})
                onclick_text = label.get("onclick")
                article_id = re.findall(r"'([^']*)'", onclick_text)[1]

                page_number = row.find("td", {"data-name": "PageNo"}).text
                edition_name = row.find("td", {"data-name": "EditionName"}).text
                edition_date = row.find("td", {"data-name": "editionDate"}).text
                title = label.get("for")
                title = str(title)
                title = title.replace("_", " ")

                article_url = f"https://epaper.hindustantimes.com/Home/ShareArticle?OrgId={article_id}&textview=0"
                self.browser.get(article_url)

                story_body = WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.ID, "body"))
                )

                paragraphs = story_body.find_elements(By.TAG_NAME, "p")
                article_content = " ".join([p.text for p in paragraphs])

                article_data = {
                    "title": title,
                    "article_content": article_content,
                    "edition_name": edition_name,
                    "edition_date": edition_date,
                    "page_number": page_number,
                }
                self.items.append(article_data)
        except Exception as e:
            msg = f"Error on page {page_num}: {e}"
        else:
            msg = f"Scraped page {page_num} successfully"
        return msg

    def save(self):
        df = pd.DataFrame(self.items)
        df = df.drop_duplicates()
        assert df is not None, "Empty DataFrame!"
        buf = BytesIO()
        df.to_csv(buf)
        fmt = "%d-%m-%Y"
        file = File(
            buf.getvalue(),
            f"HindustanTimes_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
        )
        self.cloud.upload_file(file, "1tQs4MpKyco1F5UuxZnGO9Jj9IQHhGmEe")

    def scrape(self):
        futures: list[Future] = []
        with ThreadPoolExecutor() as e:
            for ed_id in range(1, 60):
                for page_num in range(1, 11):
                    print(f"Submitted {ed_id} {page_num}")
                    fut = e.submit(self.scrape_one, ed_id, page_num)
                    futures.append(fut)
        for fut in futures:
            print(fut.result())
        self.save()
