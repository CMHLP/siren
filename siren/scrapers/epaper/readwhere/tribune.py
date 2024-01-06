from yarl import URL
from .core import BaseReadwhereScraper

__all__ = ("TribuneScraper",)


class TribuneScraper(BaseReadwhereScraper):
    BASE_URL = URL("https://epaper.tribuneindia.com/")
    EDITIONS = {
        "702": "Jalandhar Edition",
        "684": "Bathinda Edition",
        "109": "Ludhiana Tribune",
        "691": "Life+Style (Ldh)",
        "106": "The Tribune",
        "686": "Jalandhar Tribune",
        "690": "Delhi Edition",
        "780": "Haryana Edition",
        "108": "Life+Style (Chd)",
        "685": "Amritsar Tribune",
        "299": "Chandigarh Tribune",
        "687": "Himachal Edition",
    }
