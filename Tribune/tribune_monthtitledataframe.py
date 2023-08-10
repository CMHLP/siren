import os
import re
import time
from datetime import datetime

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

chrome_driver_path = os.environ.get("CHROMEDRIVER_PATH")


def main():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    service = ChromeService(executable_path=chrome_driver_path)
    browser = webdriver.Chrome(service=service, options=options)

    date_today = datetime.now().strftime("%d-%b-%Y")

    browser.get(
        "https://www.readwhere.com/user/loginv3?client=rwconnectV3&xdm_key=xdm_key_1684737739&client_id=1640941005&main_window_url=https%3A%2F%2Fepaper.tribuneindia.com%2Fuser%2Fmypurchase"
    )
    browser.find_element(By.ID, "resend").send_keys("imho@cmhlp.org")
    browser.find_element(By.ID, "signinform-password").send_keys("imho2020")
    browser.find_element(
        By.XPATH,
        '//button[@type="submit" and @class="btn btn-primary" and @onclick="return submit_fun_signin()"]',
    ).click()

    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    browser.save_screenshot("screenshot.png")
    ids = [
        "780 - Haryana",
        "687 - Himachal",
        "690 - Delhi",
        "684 - Bathinda",
        "702 - Jalandhar",
    ]

    for id_entry in ids:
        id_number = id_entry.split(" - ")[0].strip()
        id_edition = id_entry.split(" - ")[1].strip()
        url = f"https://epaper.tribuneindia.com/t/{id_number}"

        browser.get(url)
        html_content = browser.page_source
        soup = BeautifulSoup(html_content, "lxml")
        script_text = soup.find("script", text=re.compile(r"'latest_vol'\s*:\s*(\d+)"))
        if script_text:
            latest_vol_match = re.search(
                r"'latest_vol'\s*:\s*(\d+)", script_text.string
            )
            if latest_vol_match:
                latest_vol = latest_vol_match.group(1)
                print(f"Latest volume for {id_entry}: {latest_vol}")

                edition_page_urls = {
                    "Haryana": f"https://epaper.tribuneindia.com/{latest_vol}/Haryana-Edition/HR-{date_today}#page/",
                    "Himachal": f"https://epaper.tribuneindia.com/{latest_vol}/Himachal-Edition/HE-{date_today}#page/",
                    "Delhi": f"https://epaper.tribuneindia.com/{latest_vol}/Delhi-Edition/NCR-{date_today}#page/",
                    "Bathinda": f"https://epaper.tribuneindia.com/{latest_vol}/Bathinda-Edition/BTI-{date_today}#page/",
                    "Jalandhar": f"https://epaper.tribuneindia.com/{latest_vol}/Jalandhar-Edition/JLE-{date_today}#page/",
                }

                base_url = edition_page_urls[id_edition]

                screenshot_folder = f"./screenshots/{id_edition}"
                if not os.path.exists(screenshot_folder):
                    os.makedirs(screenshot_folder)

                for i in range(1, 12):
                    page_url = f"{base_url}{i}/2"
                    browser.get(page_url)

                    browser.execute_script("document.body.style.zoom = '50%'")
                    time.sleep(10)

                    screenshot_path1 = f"{screenshot_folder}/{date_today}-{id_edition}-Page{i}-Part1.png"
                    browser.save_screenshot(screenshot_path1)

                    browser.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight);"
                    )
                    time.sleep(10)

                    screenshot_path2 = f"{screenshot_folder}/{date_today}-{id_edition}-Page{i}-Part2.png"
                    browser.save_screenshot(screenshot_path2)

            else:
                print(f"Latest volume for {id_entry} not found.")
        else:
            print(f"Latest volume for {id_entry} not found.")
    browser.quit()


main()
