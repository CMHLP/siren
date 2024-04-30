from collections.abc import Coroutine
from typing import Any, Protocol, Literal
from asyncio import BoundedSemaphore
from logging import getLogger

logger = getLogger(__name__)

type JSON = dict[Any, Any]


class ResponseProto(Protocol):
    status_code: int

    @property
    def content(self) -> bytes: ...

    @property
    def url(self) -> Any: ...

    @property
    def text(self) -> str: ...

    def json(self) -> JSON: ...


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
    ) -> ResponseProto: ...

    async def post(
        self,
        url: str,
        *,
        content: Any = None,
        data: Any = None,
        files: Any = None,
        json: Any = None,
        params: Any = None,
        headers: Any = None,
        cookies: Any = None,
        auth: Any = None,
        follow_redirects: Any = None,
        timeout: Any = None,
        extensions: Any = None,
    ) -> ResponseProto: ...


class OptionalSemaphore(BoundedSemaphore):
    """A BoundedSemaphore that allows unlimited acquisitions"""

    def __init__(self, value: int | None = None):
        self._block = bool(value)
        super().__init__(value or 0)

    async def acquire(self) -> Literal[True]:
        if self._block:
            return await super().acquire()
        return True

    def release(self) -> None:
        if self._block:
            return super().release()


class HTTP:
    """Wrapper for the HTTP client for fine-grained control over request concurrency"""

    def __init__(self, client: ClientProto, *, max_concurrency: int | None = None):
        self.client = client
        self.max_concurrency = max_concurrency
        self.sem = OptionalSemaphore(max_concurrency)

    async def limit_concurrency[T](self, coro: Coroutine[Any, Any, T]) -> T:
        await self.sem.acquire()
        try:
            resp = await coro
        finally:
            self.sem.release()
        return resp

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
        return await self.limit_concurrency(
            self.client.get(
                url,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
        )

    async def post(
        self,
        url: str,
        *,
        content: Any = None,
        data: Any = None,
        files: Any = None,
        json: Any = None,
        params: Any = None,
        headers: Any = None,
        cookies: Any = None,
        auth: Any = None,
        follow_redirects: Any = None,
        timeout: Any = None,
        extensions: Any = None,
    ) -> ResponseProto:
        return await self.limit_concurrency(
            self.client.post(
                url,
                content=content,
                data=data,
                files=files,
                json=json,
                params=params,
                headers=headers,
                cookies=cookies,
                auth=auth,
                follow_redirects=follow_redirects,
                timeout=timeout,
                extensions=extensions,
            )
        )
