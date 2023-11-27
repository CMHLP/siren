from yarl import URL

from .core import BaseReadwhereScraper

__all__ = ("TNIEScraper",)


class TNIEScraper(BaseReadwhereScraper):
    BASE_URL = URL("https://epaper.newindianexpress.com")
    EDITIONS = {
        "6539": "The New Indian Express-Kollam",
        "3469": "The New Indian Express-Kozhikode",
        "11447": "The New Indian Express-Kannur",
        "5605": "The New Indian Express-Sambalpur",
        "11782": "The New Indian Express-Jeypore",
        "3359": "The New Indian Express-Bhubaneswar",
        "3353": "The New Indian Express-Chennai",
        "3463": "The New Indian Express-Vishakapatnam",
        "3464": "The New Indian Express-Vijayawada",
        "3381": "The New Indian Express-Hyderabad",
        "3357": "The New Indian Express-Bengaluru",
        "3358": "The New Indian Express-Kochi",
        "3468": "The New Indian Express-Thiruvananthapuram",
        "3361": "The New Indian Express-Madurai",
        "3480": "The New Indian Express-Tirunelveli",
        "3360": "The New Indian Express-Coimbatore",
        "3455": "The New Indian Express-Tiruchy",
        "11449": "The New Indian Express-Nagapattinam",
        "3466": "The New Indian Express-Hubballi",
        "28559": "The New Indian Express-Mysuru",
        "4619": "The New Indian Express-Shivamogga",
        "3456": "The New Indian Express-Vellore",
        "3458": "The New Indian Express-Dharmapuri",
        "8681": "The New Indian Express-Tadepalligudem",
        "8680": "The New Indian Express-Anantapur",
        "5601": "The New Indian Express-Kottayam",
        "3511": "The New Indian Express-Tirupati",
        "11448": "The New Indian Express-Thrissur ",
        "22689": "The New Indian Express-Kalaburagi",
        "3467": "The New Indian Express-Belagavi",
        "3474": "The New Indian Express-Mangaluru",
    }
