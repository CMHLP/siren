from yarl import URL
from .core import BaseReadwhereScraper

__all__ = ("TIEScraper",)


class TIEScraper(BaseReadwhereScraper):
    BASE_URL = URL("https://epaper.indianexpress.com/")
    EDITIONS = {
        "271": "CHANDIGARH",
        "336": "KOLKATA",
        "10015": "JAIPUR",
        "433": "LUCKNOW",
        "300": "AHMEDABAD",
        "266": "PUNE",
        "236": "MUMBAI",
        "226": "DELHI",
    }
