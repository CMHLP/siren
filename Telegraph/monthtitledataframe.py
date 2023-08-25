import os
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from time import perf_counter

import cv2
import numpy as np
import pandas as pd
import pytesseract
import requests
from bs4 import BeautifulSoup, Tag
from PIL import Image, UnidentifiedImageError
from generics.cloud import Cloud, File

from generics.scraper import BaseScraper


class TGScraper(BaseScraper):
    edition_ids = {
        "calcutta": "71",
        "south bengal": "72",
        "north bengal": "73",
    }

    keywords = ["suicide", "kills self", "ends life"]

    df_columns = ["date", "edition", "page", "region", "title", "text", "image_url"]

    def __init__(self, start: datetime, end: datetime, cloud: Cloud):
        self.start = start
        self.end = end
        self.cloud = cloud
        self.items = []
        self.executor = ThreadPoolExecutor()

    def scrape(self):
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'

        # Loop through the last 30 days

        futures = []

        start = perf_counter()
        cur = self.start
        print(f"Starting scraper from {cur}")
        while cur != self.end:
            date_today = cur.strftime("%Y-%m-%d")
            for edition_name, edition_id in self.edition_ids.items():
                for count in range(1, 14):
                    fut = self.executor.submit(
                        self.scrape_one, date_today, edition_name, edition_id, count
                    )
                    futures.append(fut)
            cur += timedelta(days=1)

        print(f"Submitted {len(futures)} futures")
        done, notdone = wait(futures)
        print(f"Completed {len(done)} / {len(done)+len(notdone)} futures")
        self.executor.shutdown()

        # Create a DataFrame from the list
        result_df = pd.DataFrame(self.items, columns=self.df_columns)
        result_df = result_df.drop_duplicates()
        assert result_df is not None
        buf = StringIO()
        result_df.to_csv(buf)
        buf.seek(0)
        fmt = "%d-%m-%Y"
        file = File(
            buf.read().encode(),
            f"TG_{self.start.strftime(fmt)}_{self.end.strftime(fmt)}.csv",
        )
        self.cloud.upload_file(file, "1tQs4MpKyco1F5UuxZnGO9Jj9IQHhGmEe")

        print(f"Finished in {perf_counter() - start}s")

    # Function to divide image into regions
    def get_regions(self, image):
        width, height = image.size
        one_third_width = width // 3
        one_third_height = height // 3

        regions = {}
        region_names = [
            "Top Left",
            "Top Middle",
            "Top Right",
            "Center Left",
            "Center Middle",
            "Center Right",
            "Bottom Left",
            "Bottom Middle",
            "Bottom Right",
        ]

        for row in range(3):
            for col in range(3):
                left = col * one_third_width
                top = row * one_third_height
                right = (col + 1) * one_third_width
                bottom = (row + 1) * one_third_height
                region = image.crop((left, top, right, bottom))
                region_name = region_names[row * 3 + col]
                regions[region_name] = region
        return regions

    def find_word_in_regions(self, regions):
        for region_name, region_image in regions.items():
            text = pytesseract.image_to_string(region_image, lang="eng")
            if "suicide" in text.lower():
                return region_name
            else:
                continue

    def keyword_region(self, resp):
        sp = BeautifulSoup(resp.content, "html.parser")
        for img in sp.find_all("img"):
            if img.has_attr("usemap"):
                imgsrc = img["src"]
                if imgsrc:
                    imgresponse = requests.get(imgsrc)
                    # print(f"region image {imgsrc}")
                    image = Image.open(BytesIO(imgresponse.content))
                    regions = self.get_regions(image)
                    region = self.find_word_in_regions(regions)
                    if region:
                        print(f"found keywords in region: {region}")
                    return region

    # Function to get the title from the OCR data
    def get_title(self, imag):
        # Read the image and convert it to grayscale
        open_cv_image = np.array(imag)
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        gray_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

        # Apply the thresholding with the provided values
        _, binary_image = cv2.threshold(
            gray_image, 10, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )

        contours, _ = cv2.findContours(
            ~binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        contour_heights = [cv2.boundingRect(c)[3] for c in contours]
        avg_height = sum(contour_heights) / len(contour_heights)

        blank_image = 255 * np.ones_like(gray_image)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if h > avg_height:
                cv2.drawContours(blank_image, [c], 0, (0, 0, 0), thickness=cv2.FILLED)

        new_image = 255 * np.ones_like(open_cv_image)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if h > avg_height:
                cv2.rectangle(blank_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                # Copy the bounding boxes with content from the original image
                new_image[y : y + h, x : x + w] = open_cv_image[y : y + h, x : x + w]

        tit = pytesseract.image_to_string(new_image)
        tit = tit.replace("\n", " ")
        tit = tit[0:50]
        return tit

    def scrape_one(self, date_today, edition_name, edition_id, count):
        url = f"https://epaper.telegraphindia.com/{edition_name}/{date_today}/{edition_id}/Page-{str(count)}.html"
        response = requests.get(url)
        # print(f"page no: {count}\n")
        reg = self.keyword_region(response)
        soup = BeautifulSoup(response.content, "html.parser")
        showpop_elements = []
        for area in soup.find_all("area"):
            onclick = area.get("onclick")
            if onclick and (
                "show_popclink" in onclick
                or "show_pophead" in onclick
                or "show_pop" in onclick
            ):
                showpop_elements.append(area)

        for showpop_element in showpop_elements:
            onclick = showpop_element.get("onclick")
            if onclick:
                onclick_parts = onclick.split(",")
                newspaper_id = onclick_parts[0].split("'")[1]
                publication_id = onclick_parts[1].split("'")[1]

                image_url = f"https://epaper.telegraphindia.com/imageview/{newspaper_id}/{publication_id}/{edition_id}.html"

                # #print(f'image_url: {image_url}\n')
                response = requests.get(image_url)
                image_page_soup = BeautifulSoup(response.content, "html.parser")

                img_element = image_page_soup.find("img", onclick="zoomin(this.id);")
                assert isinstance(img_element, Tag)

                if img_element:
                    img_src = img_element.get("src")
                    if img_src:
                        assert isinstance(img_src, str)
                        img_response = requests.get(img_src)

                        try:
                            img = Image.open(BytesIO(img_response.content))

                            extracted_text = pytesseract.image_to_string(
                                img, lang="eng"
                            )
                            # extracted_text = extracted_text.replace('\n', ' ')
                            # img_text = pytesseract.image_to_string(Image.open(BytesIO(response.content)))
                            if any(
                                [
                                    keyword in extracted_text.lower()
                                    for keyword in self.keywords
                                ]
                            ):
                                extracted_text = extracted_text.replace("\n", " ")
                                try:
                                    title = self.get_title(img)
                                except Exception as e:
                                    # print(f"Error encountered in title extraction: {e}")
                                    title = ""

                                # page_folder = os.path.join("telegraph_images", edition_name, date_today,
                                #                            f"Page-{count}")
                                # if not os.path.exists(page_folder):
                                #     os.makedirs(page_folder)
                                # image_name = f"{date_today}_{newspaper_id}_{publication_id}_{count}_{edition_name}.jpg"
                                # image_path = os.path.join(page_folder, image_name)
                                # with open(image_path, "wb") as f:
                                #     f.write(img_response.content)
                                #     #print(f"Saved {image_name} to {page_folder} folder")
                                # #print(str(lst[-1]))
                                self.items.append(
                                    [
                                        date_today,
                                        edition_name,
                                        str(count),
                                        reg,
                                        title,
                                        extracted_text,
                                        image_url,
                                    ]
                                )
                        except UnidentifiedImageError:
                            # print(f"Failed to identify image")
                            continue
