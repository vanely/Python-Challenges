"""Day 8 — async HTTP with httpx. Needs network."""
import asyncio
import time

import httpx

URLS = [f"https://httpbin.org/delay/{d}" for d in (1, 1, 1, 1)]


async def fetch_one(client: httpx.AsyncClient, url: str) -> tuple[str, int, float]:
    t0 = time.perf_counter()
    try:
        r = await client.get(url)
        return url, r.status_code, time.perf_counter() - t0
    except httpx.HTTPError as e:
        return url, -1, time.perf_counter() - t0


async def main() -> None:
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=10) as client:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_one(client, u)) for u in URLS]
    for url, status, secs in (t.result() for t in tasks):
        print(f"{status:>4}  {secs:5.2f}s  {url}")
    print(f"total {time.perf_counter() - t0:.2f}s for {len(URLS)} requests of ~1s each")


if __name__ == "__main__":
    asyncio.run(main())
