"""0.3 — Cancellation semantics. Predict every line of output before running."""
import asyncio
import contextlib


async def worker(name: str, steps: int = 5) -> str:
    try:
        for i in range(steps):
            print(f"  {name}: step {i} (about to await)")
            await asyncio.sleep(0.01)          # cancellation can only land HERE
            print(f"  {name}: step {i} resumed")
        return f"{name} done"
    except asyncio.CancelledError:
        print(f"  {name}: CancelledError caught in coroutine")
        raise                                  # ALWAYS re-raise
    finally:
        print(f"  {name}: finally runs")


async def demo_basic() -> None:
    print("--- basic: cancel lands at the await where the task is suspended ---")
    t = asyncio.create_task(worker("A"))
    await asyncio.sleep(0)                     # let it start (runs to first await)
    t.cancel()
    print("  cancel() requested; nothing happened yet:", t.cancelled(), t.cancelling())
    with contextlib.suppress(asyncio.CancelledError):
        await t
    print("  awaited:", t.cancelled(), t.done())


async def demo_no_await_no_cancel() -> None:
    print("--- code between awaits is never interrupted ---")

    async def busy() -> int:
        total = 0
        for i in range(200_000):               # no await: cannot be cancelled mid-loop
            total += i
        await asyncio.sleep(0)                 # first opportunity
        return total

    t = asyncio.create_task(busy())
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        print("  cancelled only once it reached an await")


async def demo_swallowing_is_a_bug() -> None:
    print("--- swallowing CancelledError ---")

    async def bad() -> str:
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            return "swallowed"                 # DON'T. Caller thinks task finished normally.
        return "unreachable"

    t = asyncio.create_task(bad())
    await asyncio.sleep(0)
    t.cancel()
    print("  result:", await t, "| cancelled():", t.cancelled())   # 'swallowed' False


async def demo_finally_await() -> None:
    print("--- awaiting inside finally during cancellation ---")

    async def cleanup_needs_await() -> None:
        try:
            await asyncio.sleep(1)
        finally:
            print("  cleanup: awaiting (can be cancelled AGAIN if canceller is impatient)")
            await asyncio.sleep(0.01)
            print("  cleanup: finished")

    t = asyncio.create_task(cleanup_needs_await())
    await asyncio.sleep(0)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t

    async def shielded_cleanup() -> None:
        try:
            await asyncio.sleep(1)
        finally:
            await asyncio.shield(asyncio.sleep(0.01))   # protected from a 2nd cancel
            print("  shielded cleanup finished")

    t = asyncio.create_task(shielded_cleanup())
    await asyncio.sleep(0)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t


async def demo_shield() -> None:
    print("--- shield: outer is cancelled, inner keeps running ---")
    inner_done = asyncio.Event()

    async def commit() -> None:
        await asyncio.sleep(0.02)
        print("  inner commit completed despite outer cancel")
        inner_done.set()

    async def outer() -> None:
        await asyncio.shield(commit())

    t = asyncio.create_task(outer())
    await asyncio.sleep(0)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t
    print("  outer cancelled:", t.cancelled())
    await inner_done.wait()


async def demo_uncancel() -> None:
    print("--- 3.11+: cancelling() counter and timeout() ---")

    async def slow() -> None:
        await asyncio.sleep(1)

    try:
        async with asyncio.timeout(0.01):      # uses cancel() + uncancel() internally
            await slow()
    except TimeoutError:
        print("  TimeoutError, and current task is NOT left cancelled:",
              asyncio.current_task().cancelling())  # type: ignore[union-attr]


async def demo_to_thread() -> None:
    print("--- cancelling to_thread cancels the await, not the thread ---")
    import time
    flag = {"ran": False}

    def blocking() -> None:
        time.sleep(0.05)
        flag["ran"] = True

    t = asyncio.create_task(asyncio.to_thread(blocking))
    await asyncio.sleep(0)
    t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await t
    await asyncio.sleep(0.08)
    print("  thread still completed:", flag["ran"])


async def main() -> None:
    await demo_basic()
    await demo_no_await_no_cancel()
    await demo_swallowing_is_a_bug()
    await demo_finally_await()
    await demo_shield()
    await demo_uncancel()
    await demo_to_thread()


if __name__ == "__main__":
    asyncio.run(main())
