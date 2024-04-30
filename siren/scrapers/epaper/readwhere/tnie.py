from yarl import URL

from .core import BaseReadwhereScraper

__all__ = ("TNIEScraper",)


class TNIEScraper(BaseReadwhereScraper):
    BASE_URL = URL("https://epaper.newindianexpress.com/")

    EDITIONS = {
        "6539": "Kollam",
        "3469": "Kozhikode",
        "11447": "Kannur",
        "5605": "Sambalpur",
        "11782": "Jeypore",
        "3359": "Bhubaneswar",
        "3353": "Chennai",
        "3463": "Vishakapatnam",
        "3464": "Vijayawada",
        "3381": "Hyderabad",
        "3357": "Bengaluru",
        "3358": "Kochi",
        "3468": "Thiruvananthapuram",
        "3361": "Madurai",
        "3480": "Tirunelveli",
        "3360": "Coimbatore",
        "3455": "Tiruchy",
        "11449": "Nagapattinam",
        "3466": "Hubballi",
        "28559": "Mysuru",
        "4619": "Shivamogga",
        "3456": "Vellore",
        "3458": "Dharmapuri",
        "8681": "Tadepalligudem",
        "8680": "Anantapur",
        "5601": "Kottayam",
        "3511": "Tirupati",
        "11448": "Thrissur ",
        "22689": "Kalaburagi",
        "3467": "Belagavi",
        "3474": "Mangaluru",
    }
