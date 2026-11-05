"""T3 w3 — threads and processes from asyncio, context propagation, structured shutdown."""
from __future__ import annotations

import asyncio
import contextvars
import logging
import multiprocessing as mp
import os
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

ctx_user: contextvars.ContextVar[str] = contextvars.ContextVar("user", default="anon")


def who() -> str:
    return f"{ctx_user.get()} in {threading.current_thread().name}"


def cpu(n: int) -> int:
    return sum(i * i for i in range(n)) % 1000


def blocking_io() -> str:
    time.sleep(0.05)
    return who()


async def demo_propagation() -> None:
    print("=== contextvars propagation into threads ===")
    ctx_user.set("ada")
    loop = asyncio.get_running_loop()
    print("  to_thread:      ", await asyncio.to_thread(who))                  # copies context
    print("  run_in_executor:", await loop.run_in_executor(None, who))         # does NOT
    print("  fixed:          ", await loop.run_in_executor(None, contextvars.copy_context().run, who))


async def demo_pools() -> None:
    print("=== thread pool for I/O, process pool for CPU, shut down in order ===")
    ctx = mp.get_context("spawn")            # never fork from a threaded/async process
    tpool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="io")
    ppool = ProcessPoolExecutor(max_workers=os.cpu_count() or 2, mp_context=ctx)
    loop = asyncio.get_running_loop()
    try:
        t0 = time.perf_counter()
        io_results, cpu_results = await asyncio.gather(
            asyncio.gather(*(loop.run_in_executor(tpool, blocking_io) for _ in range(16))),
            asyncio.gather(*(loop.run_in_executor(ppool, cpu, 300_000) for _ in range(4))),
        )
        print(f"  16 blocking I/O + 4 CPU jobs in {time.perf_counter() - t0:.2f}s")
        print("  ", io_results[0], cpu_results)
    finally:
        # order: stop submitting -> drain/cancel loop tasks -> executors (cancel queued futures)
        tpool.shutdown(wait=True, cancel_futures=True)
        ppool.shutdown(wait=True, cancel_futures=True)
        print("  pools shut down cleanly")


async def demo_cancel_vs_executor() -> None:
    print("=== cancelling an executor future cancels the await, not the work ===")
    loop = asyncio.get_running_loop()
    started, done = threading.Event(), threading.Event()

    def slow() -> None:
        started.set()
        time.sleep(0.1)
        done.set()

    fut = loop.run_in_executor(None, slow)
    await asyncio.to_thread(started.wait)     # make sure the thread is RUNNING (a not-yet-started
    fut.cancel()                              # concurrent.futures future CAN be cancelled outright)
    await asyncio.sleep(0.15)
    print("  thread finished anyway:", done.is_set(), "| future cancelled:", fut.cancelled())


class ContextFilter(logging.Filter):
    def filter(self, r: logging.LogRecord) -> bool:
        r.user = ctx_user.get()
        return True


async def demo_logging() -> None:
    print("=== request-scoped logging without passing ids around ===")
    logging.basicConfig(level=logging.INFO, format="  [%(user)s] %(message)s", force=True)
    logging.getLogger().addFilter(ContextFilter())

    async def handle(user: str) -> None:
        ctx_user.set(user)
        logging.info("start")
        await asyncio.to_thread(lambda: logging.info("from worker thread"))
        logging.info("end")

    async with asyncio.TaskGroup() as tg:
        for u in ("ada", "bob"):
            tg.create_task(handle(u))


async def main() -> None:
    await demo_propagation()
    await demo_pools()
    await demo_cancel_vs_executor()
    await demo_logging()


if __name__ == "__main__":
    asyncio.run(main())
