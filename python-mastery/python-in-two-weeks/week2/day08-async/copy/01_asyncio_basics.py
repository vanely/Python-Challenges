"""Day 8 — asyncio essentials."""
import asyncio
import time
from collections.abc import AsyncIterator


async def fetch(name: str, delay: float) -> str:
    print(f"  start {name}")
    await asyncio.sleep(delay)          # NOT time.sleep — that would block the loop
    print(f"  done  {name}")
    return name.upper()


async def sequential() -> None:
    t0 = time.perf_counter()
    a = await fetch("a", 0.2)
    b = await fetch("b", 0.2)
    print(a, b, f"{time.perf_counter() - t0:.2f}s (sequential)")


async def concurrent_gather() -> None:
    t0 = time.perf_counter()
    results = await asyncio.gather(fetch("a", 0.2), fetch("b", 0.2), fetch("c", 0.1))
    print(results, f"{time.perf_counter() - t0:.2f}s (gather)")


async def concurrent_taskgroup() -> None:
    """3.11+ structured concurrency: if one fails, the rest are cancelled."""
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("x", 0.1))
        t2 = tg.create_task(fetch("y", 0.1))
    print(t1.result(), t2.result(), "(taskgroup)")


async def with_timeout() -> None:
    try:
        async with asyncio.timeout(0.05):
            await fetch("slow", 1.0)
    except TimeoutError:
        print("timed out")


async def bounded(n_jobs: int, limit: int) -> None:
    sem = asyncio.Semaphore(limit)

    async def job(i: int) -> int:
        async with sem:                         # at most `limit` inside at once
            await asyncio.sleep(0.05)
            return i

    results = await asyncio.gather(*(job(i) for i in range(n_jobs)))
    print(f"bounded: {len(results)} jobs, max {limit} concurrent")


async def errors() -> None:
    async def boom() -> None:
        raise ValueError("bad")

    results = await asyncio.gather(fetch("ok", 0.01), boom(), return_exceptions=True)
    print("allSettled-style:", results)


async def ticker(n: int) -> AsyncIterator[int]:
    """Async generator."""
    for i in range(n):
        await asyncio.sleep(0.01)
        yield i


async def consume() -> None:
    async for i in ticker(3):
        print("tick", i)
    squares = [i * i async for i in ticker(3)]  # async comprehension
    print(squares)


async def blocking_in_thread() -> None:
    """Run a blocking function without stalling the loop."""
    result = await asyncio.to_thread(time.sleep, 0.05)
    print("to_thread ok", result)


async def main() -> None:
    await sequential()
    await concurrent_gather()
    await concurrent_taskgroup()
    await with_timeout()
    await bounded(20, 5)
    await errors()
    await consume()
    await blocking_in_thread()

    # a coroutine that is never awaited: RuntimeWarning
    # fetch("never", 1)


if __name__ == "__main__":
    asyncio.run(main())                         # the only place you start a loop
