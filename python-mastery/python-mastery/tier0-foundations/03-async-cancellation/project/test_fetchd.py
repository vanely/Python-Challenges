import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from fetchd import Fetcher, TokenBucket

pytestmark = pytest.mark.asyncio


# --- token bucket with a fake clock -----------------------------------------------------------------
async def test_token_bucket_deterministic() -> None:
    now = 0.0
    slept: list[float] = []

    def clock() -> float:
        return now

    async def fake_sleep(s: float) -> None:
        nonlocal now
        slept.append(s)
        now += s

    b = TokenBucket(rate=2.0, burst=2, clock=clock, sleep=fake_sleep)
    await b.acquire(); await b.acquire()          # burst
    assert slept == []
    await b.acquire()                             # must wait 0.5s for one token
    assert slept == [0.5]
    now += 10
    await b.acquire(); await b.acquire()          # refilled to capacity, not beyond
    await b.acquire()
    assert slept == [0.5, 0.5]


# --- mock transport helpers -------------------------------------------------------------------------------
def transport(handler):  # type: ignore[no-untyped-def]
    return httpx.MockTransport(handler)


async def test_retry_on_5xx_not_4xx() -> None:
    calls: dict[str, int] = {}

    async def handler(req: httpx.Request) -> httpx.Response:
        calls[req.url.path] = calls.get(req.url.path, 0) + 1
        if req.url.path == "/flaky":
            return httpx.Response(503 if calls["/flaky"] == 1 else 200)
        if req.url.path == "/missing":
            return httpx.Response(404)
        return httpx.Response(200)

    async with Fetcher(retries=3, rate=1000, burst=1000, transport=transport(handler)) as f:
        results = {r.url: r async for r in f.fetch_all(["http://x/flaky", "http://x/missing", "http://x/ok"])}
    assert results["http://x/flaky"].attempts == 2 and results["http://x/flaky"].ok
    assert results["http://x/missing"].attempts == 1 and results["http://x/missing"].status == 404
    assert results["http://x/ok"].ok


async def test_transport_error_exhausts_retries() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    async with Fetcher(retries=2, rate=1000, burst=1000, transport=transport(handler)) as f:
        [r] = [r async for r in f.fetch_all(["http://x/"])]
    assert r.attempts == 2 and r.error and "transport" in r.error and not r.ok


async def test_concurrency_bound_enforced() -> None:
    active = peak = 0

    async def handler(req: httpx.Request) -> httpx.Response:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200)

    async with Fetcher(concurrency=3, rate=1000, burst=1000, transport=transport(handler)) as f:
        n = len([r async for r in f.fetch_all([f"http://x/{i}" for i in range(12)])])
    assert n == 12 and peak == 3


async def test_per_request_timeout_recorded_run_continues() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/slow":
            await asyncio.sleep(1)
        return httpx.Response(200)

    async with Fetcher(timeout=0.02, retries=1, rate=1000, burst=1000, transport=transport(handler)) as f:
        results = {r.url: r async for r in f.fetch_all(["http://x/slow", "http://x/fast"])}
    assert results["http://x/slow"].error == "timeout" and results["http://x/fast"].ok


async def test_global_deadline() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return httpx.Response(200)

    async with Fetcher(concurrency=1, rate=1000, burst=1000, transport=transport(handler)) as f:
        got = []
        with pytest.raises(TimeoutError):
            async for r in f.fetch_all([f"http://x/{i}" for i in range(20)], deadline=0.12):
                got.append(r)
    assert 1 <= len(got) <= 3


async def test_consumer_cancellation_is_clean(recwarn: pytest.WarningsRecorder) -> None:
    started = asyncio.Event()
    cancelled_inside = asyncio.Event()

    async def handler(req: httpx.Request) -> httpx.Response:
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled_inside.set()
            raise
        return httpx.Response(200)

    async with Fetcher(rate=1000, burst=1000, transport=transport(handler)) as f:

        async def consume() -> None:
            async for _ in f.fetch_all(["http://x/a", "http://x/b"]):
                pass

        t = asyncio.create_task(consume())
        await started.wait()
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t
    assert cancelled_inside.is_set()
    assert not [w for w in recwarn if "pending" in str(w.message)]


async def test_stop_prevents_new_dispatch() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.02)
        return httpx.Response(200)

    async with Fetcher(concurrency=1, rate=1000, burst=1000, transport=transport(handler)) as f:
        results = []
        async for r in f.fetch_all([f"http://x/{i}" for i in range(5)]):
            results.append(r)
            f.stop()
    assert results[0].ok and all(r.error == "cancelled" for r in results[1:])


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
async def test_sigterm_exit_code() -> None:
    script = Path(__file__).with_name("fetchd.py")
    proc = subprocess.Popen(
        [sys.executable, str(script), "http://127.0.0.1:9/never"],  # port 9 = discard; connection refused -> retries
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    time.sleep(0.5)
    os.kill(proc.pid, signal.SIGTERM)
    code = proc.wait(timeout=10)
    assert code == 143, proc.stderr.read().decode()  # type: ignore[union-attr]
