"""0.3 — Graceful shutdown. Run it, then in another terminal: kill -TERM <pid>  (or Ctrl-C).
On Windows only Ctrl-C works: there is no SIGTERM delivery (`taskkill /F` is a hard kill).

Pattern: signal -> Event; workers check the event; drain with a grace deadline; exit code.
"""
import asyncio
import logging
import os
import signal
import sys

log = logging.getLogger("svc")


async def producer(queue: asyncio.Queue[int], stop: asyncio.Event) -> None:
    n = 0
    while not stop.is_set():
        await queue.put(n)
        log.debug("produced %d", n)
        n += 1
        await asyncio.sleep(0.2)
    log.info("producer stopped after %d items", n)


async def consumer(name: str, queue: asyncio.Queue[int], stop: asyncio.Event) -> None:
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=0.5)
        except TimeoutError:
            if stop.is_set():
                break
            continue
        log.info("%s processing %d", name, item)
        await asyncio.sleep(0.7)              # simulate work that must not be torn mid-way
        queue.task_done()
        log.info("%s finished %d", name, item)
    log.info("%s exiting", name)


async def main() -> int:
    stop = asyncio.Event()
    received: dict[str, int] = {}
    loop = asyncio.get_running_loop()

    def on_signal(sig: signal.Signals) -> None:
        log.warning("received %s; beginning graceful shutdown", sig.name)
        received["sig"] = int(sig)
        stop.set()

    sigs = (signal.SIGINT, signal.SIGTERM)
    previous = {s: signal.getsignal(s) for s in sigs}
    try:
        for s in sigs:
            loop.add_signal_handler(s, on_signal, s)
        posix = True
    except NotImplementedError:                       # Windows: no loop signal API; only Ctrl-C arrives
        posix = False
        for s in sigs:
            signal.signal(s, lambda n, _f: loop.call_soon_threadsafe(on_signal, signal.Signals(n)))

    queue: asyncio.Queue[int] = asyncio.Queue(maxsize=10)
    log.info("pid %d starting", os.getpid())
    failed = False
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(producer(queue, stop))
            for i in range(2):
                tg.create_task(consumer(f"c{i}", queue, stop))
            await stop.wait()
            log.info("draining: %d items still queued", queue.qsize())
            try:
                async with asyncio.timeout(2.0):     # grace period for in-flight work
                    await queue.join()
            except TimeoutError:
                log.error("grace period expired; abandoning %d items", queue.qsize())
                raise                                # cancels the group
    except* TimeoutError:
        failed = True                                 # (return/break not allowed in except*)
    finally:
        for s in sigs:
            if posix:
                loop.remove_signal_handler(s)
            else:
                signal.signal(s, previous[s] or signal.SIG_DFL)
    if failed:
        return 1
    sig = received.get("sig")
    return 128 + sig if sig else 0                    # 130 for SIGINT, 143 for SIGTERM


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
    sys.exit(asyncio.run(main()))
