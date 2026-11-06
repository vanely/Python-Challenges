"""0.3 — TaskGroup vs gather, timeouts, bounded concurrency, task refs, contextvars."""
import asyncio
import contextvars
import random

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


async def job(name: str, delay: float, fail: bool = False) -> str:
    print(f"  [{request_id.get()}] {name} start")
    await asyncio.sleep(delay)
    if fail:
        raise ValueError(f"{name} failed")
    print(f"  [{request_id.get()}] {name} done")
    return name


async def demo_gather_keeps_siblings_running() -> None:
    print("--- gather: first exception propagates, siblings keep running ---")
    try:
        await asyncio.gather(job("g1", 0.05), job("g2", 0.01, fail=True), job("g3", 0.02))
    except ValueError as e:
        print("  caught:", e)
    await asyncio.sleep(0.06)                  # observe: g1 and g3 still finish


async def demo_taskgroup_cancels_siblings() -> None:
    print("--- TaskGroup: first exception cancels siblings, raises ExceptionGroup ---")
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(job("t1", 0.05))
            tg.create_task(job("t2", 0.01, fail=True))
            tg.create_task(job("t3", 0.02))
    except* ValueError as eg:
        print("  caught group:", [str(e) for e in eg.exceptions])
    await asyncio.sleep(0.06)                  # observe: t1/t3 never print 'done'


async def demo_gather_return_exceptions() -> None:
    print("--- gather(return_exceptions=True): allSettled ---")
    results = await asyncio.gather(job("r1", 0.01), job("r2", 0.01, fail=True), return_exceptions=True)
    print("  ", [r if not isinstance(r, BaseException) else f"ERR:{r}" for r in results])


async def demo_timeout_scope() -> None:
    print("--- timeout as a cancel scope over a whole block ---")
    try:
        async with asyncio.timeout(0.2):
            await job("a", 0.05)
            await job("b", 0.5)                # deadline hits here
            await job("c", 0.05)               # never runs
    except TimeoutError:
        print("  block timed out as a unit")


async def demo_bounded() -> None:
    print("--- bounded concurrency with Semaphore inside a TaskGroup ---")
    sem = asyncio.Semaphore(3)
    active = 0
    peak = 0

    async def limited(i: int) -> None:
        nonlocal active, peak
        async with sem:
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1

    async with asyncio.TaskGroup() as tg:
        for i in range(10):
            tg.create_task(limited(i))
    print("  peak concurrent:", peak)


class Service:
    """Fire-and-forget done right: keep references."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def spawn(self, coro: "asyncio.coroutines._CoroutineLike[None]") -> None:  # type: ignore[name-defined]
        t = asyncio.create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)   # GC-safe: set holds it until done

    async def drain(self) -> None:
        await asyncio.gather(*self._tasks, return_exceptions=True)


async def demo_task_refs() -> None:
    print("--- background tasks with references ---")
    svc = Service()
    for i in range(3):
        svc.spawn(job(f"bg{i}", random.random() * 0.02))
    await svc.drain()


async def demo_contextvars() -> None:
    print("--- contextvars: each task gets a COPY of the context at creation ---")
    request_id.set("req-1")
    async with asyncio.TaskGroup() as tg:
        tg.create_task(job("child", 0.01))    # sees req-1
        request_id.set("req-2")               # changing after creation does not affect the child
        tg.create_task(job("child2", 0.01))   # sees req-2
    print("  parent sees:", request_id.get())


async def main() -> None:
    await demo_gather_keeps_siblings_running()
    await demo_taskgroup_cancels_siblings()
    await demo_gather_return_exceptions()
    await demo_timeout_scope()
    await demo_bounded()
    await demo_task_refs()
    await demo_contextvars()


if __name__ == "__main__":
    asyncio.run(main())
