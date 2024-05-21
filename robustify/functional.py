# MIT License

# Copyright (c) 2022 Danyal Zia Khan

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from functools import cache
from typing import TYPE_CHECKING, overload

from robustify.error import MaxTriesReached
from robustify.result import Err, Ok

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from robustify.result import Result


@overload
def do[
    ReturnType, **ParamsType
](
    action: Callable[ParamsType, Awaitable[ReturnType]],
) -> DoAsync[
    ParamsType, ReturnType
]: ...


@overload
def do[
    ReturnType, **ParamsType
](action: Callable[ParamsType, ReturnType],) -> DoSync[ParamsType, ReturnType]: ...


def do[
    ReturnType, **ParamsType
](
    action: (
        Callable[ParamsType, Awaitable[ReturnType]] | Callable[ParamsType, ReturnType]
    ),
):
    """
    Create an instance of `DoSync` or `DoAsync` depending on the argument passed
    """
    if asyncio.iscoroutine(awaitable := action()):
        return DoAsync(awaitable, action)

    result = action()
    return DoSync(result, action)


class DoAsync[**ParamsType, ReturnType]:
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
    ) -> Result[ReturnType, MaxTriesReached]: ...

    @overload
    async def retry_if(
        self,
        predicate: Callable[[ReturnType], bool],
        *,
        on_retry: Callable[..., None],
        max_tries: int,
    ) -> Result[ReturnType, MaxTriesReached]: ...

    async def retry_if(  # type: ignore
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

        return Ok(self.result)  # type: ignore

    # ? Alias
    retryif = retry_if


class DoSync[**ParamsType, ReturnType]:
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


def isin[T](value: T) -> Callable[[Iterable[T]], bool]:
    """
    Returns predicate for checking if the value is present in an iterator
    """

    @cache
    def _isin(iterator: Iterable[T]):
        return value in iterator

    return _isin
