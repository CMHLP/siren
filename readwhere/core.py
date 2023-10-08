from datetime import datetime
from aiohttp import ClientSession
from pydantic import BaseModel
from yarl import URL


class PartialArticle(BaseModel):
    """
    Represents a partial Article obtained from the publishdates endpoint.

    Parameters
    ----------

    id: :class:`str`
        The Article ID

    published: :class:`datetime`
        A :class

    """

    id: str
    published: datetime


class Article(BaseModel):
    id: str
    pageNum: str
    excerpt: str
    issue_id: str
    title_id: str


class SearchResult(BaseModel):
    status: bool
    numFound: int | None = None
    start: int | None = None
    to: int | None = None
    data: list[Article] = []


class ReadwhereScraper:
    """Base implementation of a scraper for readwhere-based websites (TNIE, Tribune, etc).

    Parameters
    ----------
    start: :class:`datetime.datetime`
        The :class:`datetime.datetime` to start scraping from.

    end: :class:`datetime.datetime`
        The :class:`datetime.datetime` to stop scraping at.

    keywords: :class:`list[str]`
        The keywords to search for.

    base_url: :class:`yarl.URL`
        The Base URL of the readwhere website.

    session: :class:`aiohttp.ClientSession`
        The ClientSession to use for making requests.

    """

    def __init__(
        self,
        start: datetime,
        end: datetime,
        keywords: list[str],
        base_url: URL,
        *,
        session: ClientSession,
    ):
        self.start = start
        self.end = end
        self.keywords = keywords
        self.url = base_url
        self.session = session

    async def get_partial_articles(
        self,
        edition_id: int | str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[PartialArticle]:
        """
        Retrieves :class:`PartialArticle`s for the given edition ID. If `start` or `end` are passed here, they are prioritised over the scraper's start and end.

        Parameters
        ----------

        edition_id: :class:`int` | :class:`str`
            The Edition ID of the articles

        start: :class:`datetime.datetime` | `None` defaults to `None`
            The date and time to start scraping from.
            This parameter is for flexibility.

        end: :class:`datetime.datetime` | `None` defaults to `None`
            The date and time to stop scraping at.
            This parameter is for flexibility.

        Returns
        -------

        :class:`list[PartialArticle]`

        """
        start = start or self.start
        end = end or self.end
        url = f"https://epaper.newindianexpress.com/viewer/publishdates/{edition_id}/{int(start.timestamp())}/{int(end.timestamp())}/json"
        resp = await self.session.get(url)
        return [PartialArticle(**i) for i in await resp.json()]
