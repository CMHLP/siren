import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

import os
chrome_driver_path = os.environ.get("CHROMEDRIVER_PATH") or "chromedriver.exe"  # default to chromedriver.exe if env var missing

base_url = "https://epaper.hindustantimes.com/Home/Search?SearchText=suicide&EditionId={}&FromDate=01%2f07%2f2022&ToDate=30%2f09%2f2022&grid-column=editionDate&grid-dir=0&grid-page={}"
articles = []
service = Service(executable_path=chrome_driver_path)   
browser = webdriver.Chrome(service=service)  
browser.set_page_load_timeout(60)  

for ed_id in range(1, 60):
    for page_num in range(1, 11):
        try:
            url = base_url.format(ed_id, page_num)
            response = requests.get(url)

            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr', {'class': 'grid-row'})

            for row in rows:
                label = row.find('label', {'onclick': True})
                onclick_text = label.get('onclick')
                article_id = re.findall(r"'([^']*)'", onclick_text)[1]

                page_number = row.find('td', {'data-name': 'PageNo'}).text
                edition_name = row.find('td', {'data-name': 'EditionName'}).text
                edition_date = row.find('td', {'data-name': 'editionDate'}).text
                title = label.get('for')
                title = str(title)
                title = title.replace('_', ' ')

                article_url = f"https://epaper.hindustantimes.com/Home/ShareArticle?OrgId={article_id}&textview=0"
                browser.get(article_url)

                story_body = WebDriverWait(browser, 10).until(
                    EC.presence_of_element_located((By.ID, "body"))
                )

                paragraphs = story_body.find_elements(By.TAG_NAME, 'p')
                article_content = ' '.join([p.text for p in paragraphs])

                article_data = {
                    'title': title,
                    'article_content': article_content,
                    'edition_name': edition_name,
                    'edition_date': edition_date,
                    'page_number': page_number
                }
                articles.append(article_data)
        except Exception as e:
            print(f"Error on page {page_num}: {e}")
            continue

browser.quit()

df = pd.DataFrame(articles)
df = df.drop_duplicates()
df.to_csv('hindustantimes.csv')
