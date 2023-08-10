import os
import re
from io import BytesIO

import cv2
import numpy as np
import pandas as pd
import pytesseract
from PIL import Image


def process_images(images_folder):
    cwd = os.getcwd()
    print(images_folder)

    keywords = ["suicide", "kills self", "ends life"]

    df_columns = ["date", "edition", "page", "region", "title", "text", "image_path"]
    lst = []

    def get_regions(image):
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

    def find_word_in_regions(regions):
        for region_name, region_image in regions.items():
            text = pytesseract.image_to_string(region_image, lang="eng")
            if "suicide" in text.lower():
                return region_name
            else:
                continue

    def get_title(imag):
        open_cv_image = np.array(imag)
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        gray_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

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
                new_image[y : y + h, x : x + w] = open_cv_image[y : y + h, x : x + w]

        tit = pytesseract.image_to_string(new_image)
        tit = tit.replace("\n", " ")
        tit = tit[0:50]
        return tit

    for dirpath, dirnames, filenames in os.walk(images_folder):
        for image_file_name in filenames:
            if not (
                image_file_name.endswith(".png")
                or image_file_name.endswith(".jpeg")
                or image_file_name.endswith(".jpg")
            ):
                print(f"Skipping non-image file: {image_file_name}")
                continue

            image_path = os.path.join(dirpath, image_file_name)
            image = Image.open(image_path)

            date_today, edition_name, _, page_number, _ = image_file_name.split("-")
            page_number = re.sub("\D", "", page_number)

            print(f"Processing image file: {image_file_name}")

            regions = get_regions(image)
            region = find_word_in_regions(regions)

            extracted_text = pytesseract.image_to_string(image, lang="eng")
            keyword_found = any(
                [keyword in extracted_text.lower() for keyword in keywords]
            )

            if keyword_found:
                print(f"Keyword found in file {image_file_name}")
                extracted_text = extracted_text.replace("\n", " ")
                try:
                    title = get_title(image)
                except Exception as e:
                    print(f"Error encountered in title extraction: {e}")
                    title = ""
            else:
                print(f"No keyword found in file {image_file_name}")
                region = ""
                title = ""
                extracted_text = ""

            lst.append(
                [
                    date_today,
                    edition_name,
                    str(page_number),
                    region,
                    title,
                    extracted_text,
                    image_path,
                ]
            )

    # Create a DataFrame from the list
    result_df = pd.DataFrame(lst, columns=df_columns)
    result_df = result_df.drop_duplicates()
    result_df.to_csv(f"tribune.csv")
