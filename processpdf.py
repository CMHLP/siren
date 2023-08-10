import os
import re
from io import BytesIO

import cv2
import numpy as np
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from PIL import Image


def process_pdf(pdf_folder):
    cwd = os.getcwd()
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\\Program Files\\Tesseract-OCR\\tesseract"
    )

    # pdf_folder = f"{cwd}\\TNIE"
    print(pdf_folder)

    keywords = ["suicide", "kills self", "ends life"]

    df_columns = ["date", "edition", "page", "region", "title", "text", "pdf_path"]
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

    for pdf_file_name in os.listdir(pdf_folder):
        print(f"Processing file: {pdf_file_name}")
        if not pdf_file_name.endswith(".pdf"):
            print(f"Skipping non-PDF file: {pdf_file_name}")
            continue

        date_and_edition_match = re.search(
            r"The-New-Indian-Express-([\w-]+)-(\d{2}-\d{2}-\d{4}).pdf", pdf_file_name
        )
        if not date_and_edition_match:
            print(f"Invalid file name: {pdf_file_name}")
            continue

        edition_name, date_today = date_and_edition_match.groups()

        pdf_path = os.path.join(pdf_folder, pdf_file_name)
        print(f"Converting PDF to images: {pdf_path}")
        pdf_images = convert_from_path(pdf_path)

        page_count = 1
        for pdf_page in pdf_images:
            print(f"Processing page {page_count} of {pdf_file_name}")
            regions = get_regions(pdf_page)
            region = find_word_in_regions(regions)

            extracted_text = pytesseract.image_to_string(pdf_page, lang="eng")
            keyword_found = any(
                [keyword in extracted_text.lower() for keyword in keywords]
            )

            if keyword_found:
                print(f"Keyword found in page {page_count} of {pdf_file_name}")
                extracted_text = extracted_text.replace("\n", " ")
                try:
                    title = get_title(pdf_page)
                except Exception as e:
                    print(f"Error encountered in title extraction: {e}")
                    title = ""
            else:
                print(f"No keyword found in page {page_count} of {pdf_file_name}")
                region = ""
                title = ""
                extracted_text = ""

            lst.append(
                [
                    date_today,
                    edition_name,
                    str(page_count),
                    region,
                    title,
                    extracted_text,
                    pdf_path,
                ]
            )
            page_count += 1

    # Create a DataFrame from the list
    result_df = pd.DataFrame(lst, columns=df_columns)
    result_df = result_df.drop_duplicates()
    result_df.to_csv(f"{date_today}_output.csv")
