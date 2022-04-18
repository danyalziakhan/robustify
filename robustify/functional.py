# Copyright (c) 2022-present, All rights reserved.

# Author: Danyal Zia Khan
# Email: danyal6870@gmail.com
# Copyright (c) 2020-2022 Danyal Zia Khan
# All rights reserved.

from __future__ import annotations

import asyncio
from functools import cache
from typing import TYPE_CHECKING, Awaitable, Generic, ParamSpec, TypeVar, overload

from robustify.error import MaxTriesReached
from robustify.result import Err, Ok

if TYPE_CHECKING:
    from typing import Callable, Iterable

    from robustify.result import Result

    T = TypeVar("T")

ParamsType = ParamSpec("ParamsType")
ReturnType = TypeVar("ReturnType")


@overload
def do(  # type: ignore
    action: Callable[ParamsType, Awaitable[ReturnType]],
) -> DoAsync[ParamsType, ReturnType]:
    ...


@overload
def do(
    action: Callable[ParamsType, ReturnType],
) -> DoSync[ParamsType, ReturnType]:
    ...


def do(  # type: ignore
    action: Callable[ParamsType, Awaitable[ReturnType]]
    | Callable[ParamsType, ReturnType],
):
    """
    Create an instance of `DoSync` or `DoAsync` depending on the argument passed
    """
    if asyncio.iscoroutine(awaitable := action()):  # type: ignore
        return DoAsync(awaitable, action)  # type: ignore

    result = action()  # type: ignore
    return DoSync(result, action)


class DoAsync(Generic[ParamsType, ReturnType]):
    __slots__ = ("result", "action")

    def __init__(
        self,
        result: ReturnType,
        action: Callable[ParamsType, Awaitable[ReturnType]],
    ):
        self.result = result
        self.action = action

    @overload
    async def retry_if(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., Awaitable[None]],
        max_tries: int,
    ) -> Result[ReturnType, MaxTriesReached]:
        ...

    @overload
    async def retry_if(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., None],
        max_tries: int,
    ) -> Result[ReturnType, MaxTriesReached]:
        ...

    async def retry_if(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., Awaitable[None]] | Callable[..., None],
        max_tries: int,
    ):
        if isinstance(self.result, Awaitable):
            self.result: ReturnType = await self.result
        else:
            self.result = self.result

        for _ in range(max_tries):
            if not predicate(self.result):
                break

            if isinstance(
                coro := on_retry(), Awaitable
            ):  # ? If it isn't awaitable, then we don't need to call it again as on_retry() is already called here
                await coro

            self.result = await self.action()  # type: ignore

        else:
            return Err(
                MaxTriesReached(
                    f"Max tries ({max_tries}) reached on predicate {predicate}"
                )
            )

        return Ok(self.result)

    # ? Alias
    retryif = retry_if


class DoSync(Generic[ParamsType, ReturnType]):
    __slots__ = ("result", "action")

    def __init__(
        self,
        result: ReturnType,
        action: Callable[ParamsType, ReturnType],
    ):
        self.result = result
        self.action = action

    def retry_if(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., None],
        max_tries: int,
    ):
        for _ in range(max_tries):
            if not predicate(self.result):
                break

            on_retry()
            self.result = self.action()  # type: ignore

        else:
            return Err(
                MaxTriesReached(
                    f"Max tries ({max_tries}) reached on predicate {predicate}"
                )
            )

        return Ok(self.result)

    # ? Alias
    retryif = retry_if


def isin(value: T) -> Callable[[Iterable[T]], bool]:
    """
    Returns predicate for checking if the value is present in an iterator
    """

    @cache
    def _isin(iterator: Iterable[T]):
        return value in iterator

    return _isin
