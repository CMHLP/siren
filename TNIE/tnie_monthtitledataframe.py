from bs4 import BeautifulSoup
import re, os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from processpdftnie import process_pdf

chrome_driver_path = os.environ.get("CHROMEDRIVER_PATH")

def main():
    service = ChromeService(executable_path=chrome_driver_path)
    browser = webdriver.Chrome(service=service)

    browser.get(
        "https://www.readwhere.com/user/loginv3?client=rwconnectV3&xdm_key=xdm_key_1682054447&client_id=1590948661&main_window_url=https%3A%2F%2Fepaper.newindianexpress.com%2Fuser%2Fmypurchase")

    browser.find_element(By.ID, "resend").send_keys("imho@cmhlp.org")
    browser.find_element(By.ID, "signinform-password").send_keys("imho2020")
    browser.find_element(By.XPATH,
                         '//button[@type="submit" and @class="btn btn-primary" and @onclick="return submit_fun_signin()"]').click()

    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # browser.save_screenshot("screenshot.png")
    ids = ["3353 - Chennai", "3361 - Madurai", "3360 - Coimbatore"]
           # ,"3464 - Vijayawada", "3463 - Vishakapatnam", "3511 - Tirupati", "8680 - Anantapur", "8681 - Tadepalligudem",
           # "3381 - Hyderabad", "3455 - Tiruchy", "3480 - Tirunelveli", "3456 - Vellore", "3458 - Dharmapuri",
           # "5516 - Villupuram",
           # "11449 - Nagapattinam", "3357 - Bengaluru", "28559 - Mysuru", "3467 - Belagavi", "4619 - Shivamogga",
           # "3474 - Mangaluru",
           # "3466 - Hubballi", "22689 - Kalaburagi", "3381 - Telangana", "3358 - Kochi", "3469 - Kozhikode", "3468 - Thiruvananthapuram",
           # "5601 - Kottayam",
           # "6539 - Kollam", "11447 - Kannur", "11448 - Thrissur", "3359 - Bhubaneswar", "11782 - Jeypore",
           # "5605 - Sambalpur"]

    main_url = "https://epaper.newindianexpress.com/user/mypurchase"

    for id_entry in ids:
        id_number = id_entry.split(" - ")[0].strip()
        url = f'https://epaper.newindianexpress.com/t/{id_number}'
        browser.get(url)

        html_content = browser.page_source
        soup = BeautifulSoup(html_content, 'lxml')
        script_text = soup.find('script', text=re.compile(r"'latest_vol'\s*:\s*(\d+)"))
        if script_text:
            latest_vol_match = re.search(r"'latest_vol'\s*:\s*(\d+)", script_text.string)
            if latest_vol_match:
                latest_vol = latest_vol_match.group(1)
                print(f'Latest volume for {id_entry}: {latest_vol}')
                pdf_url = f'https://epaper.newindianexpress.com/download/newspaper/{latest_vol}'
                browser.get(pdf_url)
                time.sleep(5)
                WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "fullpdflink")))
                download_button = browser.find_element(By.CLASS_NAME, "fullpdflink")
                browser.execute_script("arguments[0].scrollIntoView();", download_button)
                time.sleep(3)  # wait for the element to be visible and interactable
                browser.execute_script("arguments[0].click();", download_button)
                time.sleep(5)  # wait for the download to complete
            else:
                print(f'Latest volume for {id_entry} not found.')
        else:
            print(f'Latest volume for {id_entry} not found.')
    browser.quit()

main()
downloads_directory = os.path.join(os.path.expanduser("~"), "Downloads")
process_pdf(downloads_directory)


