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

import functools
import inspect
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import TYPE_CHECKING, Final, NoReturn, TypeGuard

# ? An error-handling model influenced by that used by the Rust programming language
# ? See: https://doc.rust-lang.org/book/ch09-00-error-handling.html

# ? Adapted from Black's rusty.py implementation: https://github.com/psf/black/blob/main/src/black/rusty.py
# ? I also took some method implementation from result.py: https://github.com/rustedpy/result


class Ok[T]:
    """
    A value that indicates success and which stores arbitrary data for the return value.
    """

    __match_args__: Final = ("value",)
    __slots__: Final = ("_value",)

    def __init__(self, value: T) -> None:
        self._value = value

    def __repr__(self) -> str:
        return f"Ok({repr(self._value)})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Ok):
            return False

        if self.value == other.value:
            return True

        return False

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((True, self._value))

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def ok(self) -> T:
        return self._value

    def err(self) -> None:
        return None

    @property
    def value(self) -> T:
        return self._value

    def expect(self, _message: str) -> T:
        return self._value

    def expect_err(self, message: str) -> NoReturn:
        raise UnwrapError(self, message)

    def unwrap(self) -> T:
        return self._value

    def unwrap_err(self) -> NoReturn:
        raise UnwrapError(self, f"Called `Result.unwrap_err()` on an `Ok`: {self}")

    def unwrap_or[U](self, _default: U) -> T:
        return self._value


class Err[E]:
    """
    A value that signifies failure and which stores arbitrary data for the error.
    """

    __match_args__: Final = ("value",)
    __slots__: Final = ("_value",)

    def __init__(self, value: E) -> None:
        self._value = value

    def __repr__(self) -> str:
        return f"Err({repr(self._value)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Err):
            return False

        if self.value == other.value:
            return True

        return False

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return hash((False, self._value))

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def ok(self) -> None:
        return None

    def err(self) -> E:
        return self._value

    @property
    def value(self) -> E:
        return self._value

    def expect(self, message: str) -> NoReturn:
        raise UnwrapError(self, message)

    def expect_err(self, _message: str) -> E:
        return self._value

    def unwrap(self) -> NoReturn:
        raise UnwrapError(self, f"Called `Result.unwrap()` on an `Err`: {self}")

    def unwrap_err(self) -> E:
        return self._value

    def unwrap_or[U](self, default: U) -> U:
        return default


# ? A simple `Result` type inspired by Rust.
# ? See:  (https://doc.rust-lang.org/std/result/enum.Result.html)
type Result[OkType, ErrType] = Ok[OkType] | Err[ErrType]


class UnwrapError(Exception):
    """
    Exception raised from ``.unwrap_<...>`` and ``.expect_<...>`` calls.

    The original ``Result`` can be accessed via the ``.result`` attribute, but
    this is not intended for regular use, as type information is lost:
    ``UnwrapError`` doesn't know about both ``T`` and ``E``, since it's raised
    from ``Ok()`` or ``Err()`` which only knows about either ``T`` or ``E``,
    not both.
    """

    _result: Result[Any, Any]

    def __init__(self, result: Result[Any, Any], message: str) -> None:
        self._result = result
        super().__init__(message)

    @property
    def result(self) -> Result[Any, Any]:
        """
        Returns the original result.
        """
        return self._result


def returns[
    TBE: BaseException, **ParamsType, ReturnType
](
    *exceptions: type[TBE],
) -> Callable[
    [Callable[ParamsType, ReturnType]], Callable[ParamsType, Result[ReturnType, TBE]]
]:
    """
    Make a decorator to turn a function into one that returns a ``Result``.

    Regular return values are turned into ``Ok(return_value)``. Raised
    exceptions of the specified exception type(s) are turned into ``Err(exc)``.
    """
    if not exceptions or not all(
        inspect.isclass(exception) and issubclass(exception, BaseException)
        for exception in exceptions
    ):
        raise TypeError("as_result() requires one or more exception types")

    def decorator(
        fn: Callable[ParamsType, ReturnType]
    ) -> Callable[ParamsType, Result[ReturnType, TBE]]:
        """
        Decorator to turn a function into one that returns a ``Result``.
        """

        @functools.wraps(fn)
        def wrapper(
            *args: ParamsType.args, **kwargs: ParamsType.kwargs
        ) -> Result[ReturnType, TBE]:
            try:
                return Ok(fn(*args, **kwargs))
            except cast(Any, exceptions) as exc:
                return Err(exc)

        return wrapper

    return decorator


def returns_future[
    TBE: BaseException, **ParamsType, ReturnType
](*exceptions: type[TBE],) -> Callable[
    [Callable[ParamsType, Awaitable[ReturnType]]],
    Callable[ParamsType, Awaitable[Result[ReturnType, TBE]]],
]:
    """
    Make a decorator to turn a function into one that returns a ``Result``.

    Regular return values are turned into ``Ok(return_value)``. Raised
    exceptions of the specified exception type(s) are turned into ``Err(exc)``.

    Similar to @returns but for async functions
    """
    if not exceptions or not all(
        inspect.isclass(exception) and issubclass(exception, BaseException)
        for exception in exceptions
    ):
        raise TypeError("as_result_future() requires one or more exception types")

    def decorator(
        fn: Callable[ParamsType, Awaitable[ReturnType]]
    ) -> Callable[ParamsType, Awaitable[Result[ReturnType, TBE]]]:
        """
        Decorator to turn a function into one that returns a ``Result``.
        """

        @functools.wraps(fn)
        async def wrapper(
            *args: ParamsType.args, **kwargs: ParamsType.kwargs
        ) -> Result[ReturnType, TBE]:
            try:
                return Ok(await fn(*args, **kwargs))
            except cast(Any, exceptions) as exc:
                return Err(exc)

        return wrapper

    return decorator


def is_ok[OkType, ErrType](val: Result[OkType, ErrType]) -> TypeGuard[OkType]:
    """
    Shorthand for isinstance(val, Ok)
    """
    return isinstance(val, Ok)


def is_err[OkType, ErrType](val: Result[OkType, ErrType]) -> TypeGuard[ErrType]:
    """
    Shorthand for isinstance(val, Err)
    """
    return isinstance(val, Err)
