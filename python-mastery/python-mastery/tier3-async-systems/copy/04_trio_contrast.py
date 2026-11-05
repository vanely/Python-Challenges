"""T3 w4 — Tier 0.3's demos in Trio. pip install trio. Read the comments for each difference."""
import trio


async def worker(name: str) -> None:
    try:
        for i in range(5):
            print(f"  {name}: step {i}")
            await trio.sleep(0.01)            # every await is a checkpoint (cancellation can land)
    except trio.Cancelled:
        print(f"  {name}: Cancelled (must re-raise; it's BaseException like asyncio's)")
        raise


async def demo_nursery() -> None:
    print("--- nursery: no orphan tasks; first exception cancels siblings; ExceptionGroup ---")

    async def fail() -> None:
        await trio.sleep(0.02)
        raise ValueError("boom")

    try:
        async with trio.open_nursery() as n:
            n.start_soon(worker, "a")
            n.start_soon(fail)
    except* ValueError as eg:
        print("  caught:", [str(e) for e in eg.exceptions])
    # asyncio difference: create_task() can outlive its creator; in Trio a task literally cannot
    # exist outside a nursery block.


async def demo_level_triggered() -> None:
    print("--- level-triggered cancel scope: catching Cancelled doesn't un-cancel ---")
    with trio.move_on_after(0.03) as scope:
        try:
            await trio.sleep(1)
        except trio.Cancelled:
            print("  caught once...")
            raise                             # even if you didn't re-raise, the NEXT await would cancel again:
        await trio.sleep(1)                   # never reached
    print("  cancelled_caught:", scope.cancelled_caught)
    # asyncio difference: Task.cancel() is edge-triggered — catch it, swallow it, and the task keeps
    # running as if nothing happened (Tier 0.3 demo_swallowing_is_a_bug).


async def demo_timeout_shape() -> None:
    print("--- timeouts are scopes, composable, and cheap ---")
    with trio.move_on_after(0.05):           # outer
        with trio.move_on_after(1):          # inner: irrelevant, outer wins
            await trio.sleep(10)
    print("  outer deadline won")
    # asyncio.timeout() is the port of this; wait_for() was the old, task-wrapping, leaky approach.


async def demo_shield_equivalent() -> None:
    print("--- shielding = a cancel scope with shield=True ---")
    with trio.move_on_after(0.02):
        with trio.CancelScope(shield=True):
            await trio.sleep(0.05)
            print("  shielded work finished before honouring the outer cancel")
    print("  done")


async def demo_channels() -> None:
    print("--- memory channels with backpressure (bounded) ---")
    send_ch, recv_ch = trio.open_memory_channel[int](2)
    async with trio.open_nursery() as n:
        async def producer() -> None:
            async with send_ch:
                for i in range(6):
                    await send_ch.send(i)    # blocks when 2 are buffered
                    print(f"  sent {i}")

        async def consumer() -> None:
            async with recv_ch:
                async for v in recv_ch:
                    await trio.sleep(0.01)
                    print(f"  got {v}")

        n.start_soon(producer)
        n.start_soon(consumer)


async def main() -> None:
    await demo_nursery()
    await demo_level_triggered()
    await demo_timeout_shape()
    await demo_shield_equivalent()
    await demo_channels()


if __name__ == "__main__":
    trio.run(main)
