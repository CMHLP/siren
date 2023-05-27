
This script  scrapes the latest ePaper editions of The Tribune from https://epaper.tribuneindia.com using Selenium and Beautiful Soup. The script downloads the ePaper PDF files for select cities.

## Dependencies

- Python 3
- BeautifulSoup
- Selenium WebDriver

To install BeautifulSoup:

```
pip install beautifulsoup4
```

To install Selenium:

```
pip install selenium
```

You also need to download the appropriate WebDriver for your browser. This script uses ChromeDriver. Download it from https://sites.google.com/a/chromium.org/chromedriver/downloads.

## Hard Coded Variables

- `chrome_driver_path`: Set the path to the downloaded ChromeDriver executable.
- `ids`: A list of strings, containing IDs and names of the cities for which the latest ePaper edition will be downloaded.
- `login_url`: The URL of the login page for The New Indian Express ePaper website.
