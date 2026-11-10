from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any


class BackgroundTask:
    """Runs *after* the response has been fully sent. Sync callables go to a thread."""

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs

    async def __call__(self) -> None:
        if inspect.iscoroutinefunction(self.func):
            await self.func(*self.args, **self.kwargs)
        else:
            await asyncio.to_thread(self.func, *self.args, **self.kwargs)


class BackgroundTasks(BackgroundTask):
    def __init__(self) -> None:
        self.tasks: list[BackgroundTask] = []

    def add(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.tasks.append(BackgroundTask(func, *args, **kwargs))

    async def __call__(self) -> None:
        for t in self.tasks:
            await t()
