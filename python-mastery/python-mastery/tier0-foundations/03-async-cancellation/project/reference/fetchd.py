"""fetchd — bounded, rate-limited, retrying, cancellable URL fetcher."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import signal
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from dataclasses import dataclass
from types import TracebackType

import httpx

log = logging.getLogger("fetchd")


class TokenBucket:
    """`rate` tokens/second, capacity `burst`. Injectable clock+sleep for deterministic tests."""

    def __init__(
        self,
        rate: float,
        burst: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.rate, self.burst = rate, burst
        self._clock, self._sleep = clock, sleep
        self._tokens = float(burst)
        self._last = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self.burst, self._tokens + (now - self._last) * self.rate)
        self._last = now

    async def acquire(self) -> None:
        async with self._lock:              # serialise so waiters don't all wake and overshoot
            while True:
                self._refill()
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                await self._sleep((1 - self._tokens) / self.rate)


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    status: int | None
    elapsed: float
    attempts: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.status is not None and self.status < 400


class Fetcher:
    def __init__(
        self,
        *,
        concurrency: int = 10,
        rate: float = 5.0,
        burst: int = 5,
        timeout: float = 5.0,
        retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
        bucket: TokenBucket | None = None,
    ) -> None:
        self._sem = asyncio.Semaphore(concurrency)
        self._bucket = bucket or TokenBucket(rate, burst)
        self._timeout = timeout
        self._retries = retries
        self._client = httpx.AsyncClient(transport=transport, timeout=timeout)
        self._stopping = asyncio.Event()

    async def __aenter__(self) -> Fetcher:
        return self

    async def __aexit__(
        self, et: type[BaseException] | None, ev: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self._client.aclose()

    def stop(self) -> None:
        """Stop dispatching new requests and retries; in-flight attempts continue."""
        self._stopping.set()

    # --- one URL -----------------------------------------------------------------------------
    async def fetch_one(self, url: str) -> FetchResult:
        t0 = time.perf_counter()
        attempts = 0
        last_err: str | None = None
        while attempts < self._retries:
            if attempts and self._stopping.is_set():
                break                                # stopping: record the last error, no retry
            attempts += 1
            await self._bucket.acquire()
            try:
                async with asyncio.timeout(self._timeout):
                    resp = await self._client.get(url)
            except TimeoutError:
                last_err = "timeout"
            except httpx.TransportError as e:
                last_err = f"transport: {type(e).__name__}"
            else:
                if resp.status_code < 500:
                    return FetchResult(url, resp.status_code, time.perf_counter() - t0, attempts)
                last_err = f"server error {resp.status_code}"
                retry_after = resp.headers.get("retry-after")
                if retry_after and retry_after.isdigit():
                    await asyncio.sleep(float(retry_after))
                    continue
            if attempts < self._retries:
                await asyncio.sleep(min(2 ** (attempts - 1) * 0.1, 2.0) * (0.5 + random.random()))
        return FetchResult(url, None, time.perf_counter() - t0, attempts, error=last_err)

    # --- many URLs, streamed -------------------------------------------------------------------
    async def fetch_all(self, urls: Iterable[str], *, deadline: float | None = None) -> AsyncIterator[FetchResult]:
        results: asyncio.Queue[FetchResult | None] = asyncio.Queue()

        async def bounded(url: str) -> None:
            async with self._sem:
                if self._stopping.is_set():
                    await results.put(FetchResult(url, None, 0.0, 0, error="cancelled"))
                    return
                await results.put(await self.fetch_one(url))

        async def run() -> None:
            try:
                async with asyncio.timeout(deadline):
                    async with asyncio.TaskGroup() as tg:
                        for url in urls:
                            if self._stopping.is_set():
                                break
                            tg.create_task(bounded(url))
            finally:
                await results.put(None)          # sentinel, even on cancellation

        runner = asyncio.create_task(run())
        try:
            while (item := await results.get()) is not None:
                yield item
            await runner                         # surface TimeoutError / programming errors
        finally:
            if not runner.done():
                runner.cancel()
                with contextlib.suppress(asyncio.CancelledError, TimeoutError):
                    await runner


# --- CLI with graceful shutdown ---------------------------------------------------------------------
def install_signal_handlers(on_signal: Callable[[signal.Signals], None]) -> Callable[[], None]:
    """SIGINT/SIGTERM -> `on_signal` on the running loop. Returns a function that undoes it.

    POSIX uses `loop.add_signal_handler`. Windows loops don't implement it, so fall back to
    `signal.signal` + `call_soon_threadsafe`; there only SIGINT (Ctrl-C) is ever delivered —
    `kill`/`TerminateProcess` is a hard kill, so 143 can't happen on Windows.
    """
    loop = asyncio.get_running_loop()
    sigs = (signal.SIGINT, signal.SIGTERM)
    try:
        for s in sigs:
            loop.add_signal_handler(s, on_signal, s)
    except NotImplementedError:
        previous = {s: signal.getsignal(s) for s in sigs}
        for s in sigs:
            signal.signal(s, lambda n, _f: loop.call_soon_threadsafe(on_signal, signal.Signals(n)))

        def restore() -> None:
            for s, h in previous.items():
                signal.signal(s, h if h is not None else signal.SIG_DFL)

        return restore

    def remove() -> None:
        for s in sigs:
            loop.remove_signal_handler(s)

    return remove


async def main(urls: list[str], *, grace: float = 2.0) -> int:
    stop = asyncio.Event()
    sig_received: list[int] = []

    def on_signal(s: signal.Signals) -> None:
        log.warning("%s received: stopping dispatch, draining in-flight", s.name)
        sig_received.append(int(s))
        stop.set()

    uninstall = install_signal_handlers(on_signal)
    ok = failed = 0
    try:
        async with Fetcher() as f:

            async def consume() -> None:
                nonlocal ok, failed
                async for r in f.fetch_all(urls, deadline=120):
                    ok += r.ok
                    failed += not r.ok
                    log.info("%s %s %.2fs x%d %s", r.url, r.status, r.elapsed, r.attempts, r.error or "")

            consumer = asyncio.create_task(consume())
            stopper = asyncio.create_task(stop.wait())
            try:
                await asyncio.wait([consumer, stopper], return_when=asyncio.FIRST_COMPLETED)
                if not consumer.done():
                    f.stop()
                    _, pending = await asyncio.wait([consumer], timeout=grace)
                    if pending:
                        log.error("grace period (%.1fs) expired: cancelling in-flight requests", grace)
                        consumer.cancel()
                        await asyncio.wait([consumer])
                if not consumer.cancelled():
                    await consumer                   # surface the deadline / programming errors
            finally:
                for t in (consumer, stopper):
                    t.cancel()
                await asyncio.wait([consumer, stopper])
    finally:
        uninstall()
    log.info("done: %d ok, %d failed", ok, failed)
    return 128 + sig_received[0] if sig_received else (1 if failed else 0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sys.exit(asyncio.run(main(sys.argv[1:])))
