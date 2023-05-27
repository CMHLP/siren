This script downloads online newspaper pages, uses OCR to extract text from the images, and searches for certain keywords in the text. The results are saved in a CSV file.

The script hard-coded to monitor the occurrence of specific keywords in the 3 editions of the newspaper with edition_ids =
    "calcutta": "71",
    "south bengal": "72",
    "north bengal": "73", over a given period of a month.
For the current configuration it is set to search for the keywords "suicide", "kills self", and "ends life" in different editions of the Telegraph India.

The script is divided into several functions:

    get_regions(image): This function divides an image into nine equal regions (3x3 grid) and returns a dictionary with region names as keys and the cropped images as values.
    find_word_in_regions(regions): This function takes the dictionary of regions from the get_regions() function, and for each region, it extracts the text using OCR and searches for the keyword "suicide". If the keyword is found in a region, it returns the name of that region.
    keyword_region(resp): This function takes an HTTP response of a page and extracts all images from it. It then checks each image for the keyword by dividing it into regions and applying the find_word_in_regions() function.
    get_title(imag): This function takes an image, converts it to grayscale, applies thresholding and contour detection, and extracts the title from the image using OCR. The title is defined as the text within the bounding box that has a height larger than the average height of all bounding boxes in the image.
    The main part of the script loops over the past 30 days, downloads all pages of the selected editions of the newspaper, and applies the functions described above to extract the text and search for keywords.

Hardcoded Variables


    edition_ids: This dictionary contains the ID numbers of the newspaper editions to be analyzed.
    keywords: These are the keywords to search for in the text extracted from the newspaper images.

Instructions

    Install the required Python libraries, if not already installed: datetime, io, os, cv2, numpy, pandas, pytesseract, requests, PIL, bs4.
    Make sure you have the Tesseract-OCR executable installed on your machine and the path to the executable is correctly set in the script.
    Run the script using a Python interpreter.
    The script will download the images, extract text, search for keywords, and save the results in a CSV file named with the current date in the same directory as the script. The CSV file will have columns for date, edition, page, region, title, text, and image_path.

Note: The image saving part of the script is currently commented out. If you wish to save the images on your machine, uncomment the relevant lines and make sure you have the appropriate permissions to create directories and save files.

Troubleshooting

If you encounter errors during the OCR process, ensure that the Tesseract-OCR executable is correctly installed and the path is set correctly in the script.

If you encounter any other errors, check your Python environment for the correct versions of the libraries
and dependencies:

    datetime
    io
    os
    cv2
    numpy
    pandas
    pytesseract
    requests
    PIL (Pillow)
    bs4 (BeautifulSoup)

This script is highly specific to the structure of the Telegraph India e-paper website. If the website changes, it will most likely require adjustments to the URL structures, HTML parsing, and potentially the OCR and image processing parts as well.

Moreover, the efficiency and accuracy of the script highly depend on the quality of the images and the performance of the OCR. The script currently uses keyword matching, which may result in false positives (if the keyword is part of another word) and false negatives (if the keyword is misspelled or misread by the OCR).