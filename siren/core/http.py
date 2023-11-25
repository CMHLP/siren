from typing import Any, Protocol


type JSON = dict[str, str]


class ResponseProto(Protocol):
    status_code: int

    @property
    def text(self) -> str:
        ...

    def json(self) -> JSON:
        ...


class ClientProto(Protocol):
    async def get(
        self,
        url: str,
        *,
        params: Any = None,
        headers: Any = None,
        cookies: Any = None,
        auth: Any = None,
        follow_redirects: Any = None,
        timeout: Any = None,
        extensions: Any = None,
    ) -> ResponseProto:
        ...

    async def post(
        self,
        url: str,
        *,
        params: Any = None,
        headers: Any = None,
        cookies: Any = None,
        auth: Any = None,
        follow_redirects: Any = None,
        timeout: Any = None,
        extensions: Any = None,
    ) -> ResponseProto:
        ...
