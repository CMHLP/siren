
This Python script scrapes the `Hindustan Times` ePaper website for articles related to the keyword "suicide" between July 1, 2022, and September 30, 2022. The collected data includes the article title, content, edition name, edition date, and page number.

## Hardcoded Variables

- `chrome_driver_path`: Specifies the absolute path to the `chromedriver.exe` file.
- `base_url`: This URL contains the website's search query format. It will be used with string formatting to insert the required edition ID and page number. 
- `articles`: An empty list that will be filled with the scraped article data.

## Prerequisites

You will need the following Python packages installed:

- `requests`
- `beautifulsoup4`
- `pandas`
- `selenium`



You also need to download the `ChromeDriver` executable for your system. You can get it from this link: https://sites.google.com/a/chromium.org/chromedriver/downloads. Make sure to update the `chrome_driver_path` variable with the absolute path to the `chromedriver.exe` file located on your system.
Ensure that the `chromedriver` file has executable permissions. You can do this by running the following command:

```sh
chmod +x /path/to/chromedriver
```

## Methodology

1. The script uses the `requests` and `bs4` (BeautifulSoup) libraries to fetch the article listing and obtain the article's metadata such as title, edition name, edition date, and page number.
2. Selenium is used for fetching the article content, as the website renders content using JavaScript.
3. The article data is then processed, and duplicates are removed.
4. Finally, the scraped data is stored in a CSV file named `hindustantimes.csv`.

## Usage Instructions

1. Ensure you have installed the required Python packages and have the `ChromeDriver` executable in your system.
2. Update the `chrome_driver_path` variable in the script with the path to your `chromedriver.exe` file.
3. Run the script using the following command:



