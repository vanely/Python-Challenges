"""Day 8 — where the GIL matters. Run and read the timings.

Note: the CPU rows only show a speedup on a machine with >= `jobs` free cores.
On a 1–2 core container, processes and threads will look no better than sequential.
The I/O row always shows the speedup.
"""
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


def cpu_pure_python(n: int) -> int:
    """Pure-Python loop: GIL-bound."""
    total = 0
    for i in range(n):
        total += i * i % 7
    return total


def cpu_c_extension(n: int) -> str:
    """hashlib releases the GIL while hashing."""
    data = b"x" * n
    for _ in range(20):
        data = hashlib.sha256(data).digest() * (n // 32)
    return data[:4].hex()


def io_bound(secs: float) -> float:
    time.sleep(secs)                     # sleep releases the GIL
    return secs


def timed(label: str, fn: object) -> None:
    t0 = time.perf_counter()
    fn()  # type: ignore[operator]
    print(f"{label:<40} {time.perf_counter() - t0:6.2f}s")


if __name__ == "__main__":
    N = 2_000_000
    jobs = 4

    print("--- pure-Python CPU work ---")
    timed("sequential", lambda: [cpu_pure_python(N) for _ in range(jobs)])
    timed("threads (no help: GIL)", lambda: list(ThreadPoolExecutor(jobs).map(cpu_pure_python, [N] * jobs)))
    timed("processes (helps)", lambda: list(ProcessPoolExecutor(jobs).map(cpu_pure_python, [N] * jobs)))

    print("--- C-extension CPU work (hashlib) ---")
    M = 5_000_000
    timed("sequential", lambda: [cpu_c_extension(M) for _ in range(jobs)])
    timed("threads (helps: GIL released)", lambda: list(ThreadPoolExecutor(jobs).map(cpu_c_extension, [M] * jobs)))

    print("--- I/O-bound work ---")
    timed("sequential", lambda: [io_bound(0.3) for _ in range(jobs)])
    timed("threads (helps)", lambda: list(ThreadPoolExecutor(jobs).map(io_bound, [0.3] * jobs)))
