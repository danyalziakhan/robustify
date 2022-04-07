# Copyright (c) 2021-present, GYU Co., Ltd. All rights reserved.

# Author: Danyal Zia Khan
# Email: danyal6870@gmail.com
# Copyright (c) 2020-2022 Danyal Zia Khan
# All rights reserved.

# USE OF THIS SOFTWARE AND DISTRIBUTION OUTSIDE THE GYU COMPANY IS STRICTLY PROHIBITED. PLEASE REPORT ANY SUCH USE TO THE COMPANY.

from __future__ import annotations

# ? Adapted from Expression library: https://github.com/cognitedata/Expression/tree/main/expression/core
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
    if asyncio.iscoroutine(awaitable := action()):
        return DoAsync(awaitable, action)  # type: ignore

    result = action()
    return DoSync(result, action)


class DoAsync(Generic[ParamsType, ReturnType]):
    def __init__(
        self,
        result: ReturnType,
        action: Callable[ParamsType, Awaitable[ReturnType]],
    ):
        self.result = result
        self.action = action

    @overload
    async def retryif(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., Awaitable[None]],
        max_tries: int,
    ) -> Result[ReturnType, MaxTriesReached]:
        ...

    @overload
    async def retryif(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., None],
        max_tries: int,
    ) -> Result[ReturnType, MaxTriesReached]:
        ...

    async def retryif(
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

            self.result = await self.action()

        else:
            return Err(
                MaxTriesReached(f"Max tries ({max_tries}) reached for retryif()")
            )

        return Ok(self.result)

    # ? Alias
    retry_if = retryif


class DoSync(Generic[ParamsType, ReturnType]):
    def __init__(
        self,
        result: ReturnType,
        action: Callable[ParamsType, ReturnType],
    ):
        self.result = result
        self.action = action

    def retryif(
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
            self.result = self.action()

        else:
            return Err(
                MaxTriesReached(f"Max tries ({max_tries}) reached for retryif()")
            )

        return Ok(self.result)

    # ? Alias
    retry_if = retryif


def isin(value: T) -> Callable[[Iterable[T]], bool]:
    @cache
    def _isin(iterator: Iterable[T]):
        return value in iterator

    return _isin
