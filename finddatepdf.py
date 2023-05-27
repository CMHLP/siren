

import os
import re
import pytesseract
from dateutil.parser import parse
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'


def save_cropped_region(image, crop_coordinates, output_file):
    cropped_region = image.crop(crop_coordinates)
    cropped_region.save(output_file)
    print(f"Saved cropped region {crop_coordinates} to {output_file}")
    return cropped_region





def extract_date_and_location(text):
    try:
        date = parse(text, fuzzy=True)
        location = re.sub(r'\s*(\w+day,\s\w+\s\d+,\s\d+)\s*', '', text).strip()
        return date, location
    except ValueError:
        print("Could not parse the text into a date format.")
        return None, None


pdf_directory = r'D:\Pycharm_Proj\pythonProject\pdf'
output_directory = r'D:\Pycharm_Proj\pythonProject\pdf'
pdf_files = [os.path.join(pdf_directory, file) for file in os.listdir(pdf_directory) if file.lower().endswith('.pdf')]

left = 0
top = 90
right = 300
bottom = 150

for pdf_file in pdf_files:
    images = convert_from_path(pdf_file, first_page=5, last_page=5)

    for index, image in enumerate(images):
        output_file = os.path.join(output_directory,
                                   f"{os.path.splitext(os.path.basename(pdf_file))[0]}_page5_cropped.png")
        crop_coordinates = (left, top, right, bottom)
        cropped_region = save_cropped_region(image, crop_coordinates, output_file)

        text = pytesseract.image_to_string(cropped_region)
        date, location = extract_date_and_location(text)
        if date and location:
            print(f"Date: {date}, Location: {location}")
