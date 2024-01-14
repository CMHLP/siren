from yarl import URL
from siren.core import BaseScraper, Model


class NMArticle(Model):
    ...


class NMScraper(BaseScraper[NMArticle]):
    BASE_URL = URL("https://www.thenewsminute.com/search?q=suicide")
