# Copyright (c) 2022-present, All rights reserved.

# Author: Danyal Zia Khan
# Email: danyal6870@gmail.com
# Copyright (c) 2020-2022 Danyal Zia Khan
# All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING

from colorama import Fore, init

if TYPE_CHECKING:
    from typing import Final


init()


class BasicError(Exception):
    __slots__ = ("message", "url")
    __match_args__: Final = ("message", "url")

    def __init__(self, message: Exception | str, url: str | None = None) -> None:
        self.message = message
        self.url = url

        super().__init__(
            (
                Fore.RED
                + str(self.message)
                + Fore.RESET
                + Fore.CYAN
                + f" || {self.url} ||"
            )
            if self.url
            else (Fore.RED + str(self.message) + Fore.RESET)
        )


class MaxTriesReached(BasicError):
    pass
