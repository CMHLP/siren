from typing import TYPE_CHECKING
from pydantic import BaseModel


if TYPE_CHECKING:
    from yarl import URL
    from datetime import datetime


class Model(BaseModel): ...


class ResultModel(Model):
    """Standard data model containing a scraped article.

    Attributes:
        keyword: The keyword found in this article.
        content: The article's textual content.
        assets: A list of URLs to any media assets (e.g. images).
        date: The date this article was published on.


    """

    keyword: str
    content: str
    assets: list[URL]
    date: datetime
