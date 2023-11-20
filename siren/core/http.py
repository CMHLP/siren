from typing import Any, Awaitable, Protocol


type JSON = dict[str, str]


class ResponseProto(Protocol):
    status_code: int

    def json(self) -> JSON | Awaitable[JSON]:
        ...


class ClientProto(Protocol):
    async def get(self, url: str, *args: Any, **kwargs: Any) -> ResponseProto:
        ...

    async def post(self, url: str, *args: Any, **kwargs: Any) -> ResponseProto:
        ...
