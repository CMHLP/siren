import asyncio


from typing import Callable, Coroutine, Any

__all__ = ("to_thread",)


def to_thread[R, **P](fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    def inner(*args: P.args, **kwargs: P.kwargs) -> Coroutine[Any, Any, R]:
        return asyncio.to_thread(fn, *args, **kwargs)

    return inner
