"""T2 w5 — GIL-bound vs GIL-releasing work; a race the GIL hides; run on 3.13 AND 3.13t.

    python copy/04_gil_threads.py     # on a multi-core machine: threads ~1x for pure Python, ~Nx for hashlib
    uv python install 3.13t && uv run --python 3.13t copy/04_gil_threads.py
"""
import hashlib
import sys
import sysconfig
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

print(f"python {sys.version.split()[0]}  free-threaded build: {bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}",
      f" gil enabled now: {getattr(sys, '_is_gil_enabled', lambda: True)()}")
N_WORKERS = 4


def cpu_python(n: int = 3_000_000) -> int:
    return sum(i * i % 7 for i in range(n))


def cpu_c_releases_gil(n: int = 60) -> int:
    data = b"x" * 2_000_000
    for _ in range(n):
        hashlib.sha256(data).digest()      # hashlib releases the GIL for big buffers
    return n


def timed(label: str, fn, *args) -> float:  # type: ignore[no-untyped-def]
    t = time.perf_counter()
    fn(*args)
    dt = time.perf_counter() - t
    print(f"  {label:<40} {dt:6.2f}s")
    return dt


def _py(_: object) -> int:                  # module-level: ProcessPool must pickle the callable
    return cpu_python()


def _c(_: object) -> int:
    return cpu_c_releases_gil()


def with_pool(pool_cls, fn, n=N_WORKERS):  # type: ignore[no-untyped-def]
    with pool_cls(n) as ex:
        list(ex.map(fn, [None] * n))


if __name__ == "__main__":
    print("=== pure-Python CPU work ===")
    one = timed("1 call, main thread", cpu_python)
    t = timed(f"{N_WORKERS} calls, ThreadPool", with_pool, ThreadPoolExecutor, _py)
    print(f"    thread scaling: {one * N_WORKERS / t:.1f}x of ideal {N_WORKERS}x")
    p = timed(f"{N_WORKERS} calls, ProcessPool", with_pool, ProcessPoolExecutor, _py)
    print(f"    process scaling: {one * N_WORKERS / p:.1f}x (bounded by core count)")

    print("=== C work that releases the GIL (hashlib) ===")
    one = timed("1 call, main thread", cpu_c_releases_gil)
    t = timed(f"{N_WORKERS} calls, ThreadPool", with_pool, ThreadPoolExecutor, _c)
    print(f"    thread scaling: {one * N_WORKERS / t:.1f}x")

    print("=== the race the GIL mostly hides ===")
    counter = 0

    def bump(n: int = 200_000) -> None:
        global counter
        for _ in range(n):
            counter += 1                    # LOAD / ADD / STORE: not atomic

    ts = [threading.Thread(target=bump) for _ in range(4)]
    for th in ts: th.start()
    for th in ts: th.join()
    print(f"  expected 800000, got {counter}  ({'lost updates!' if counter != 800000 else 'lucky'})")

    counter = 0
    lock = threading.Lock()

    def bump_locked(n: int = 200_000) -> None:
        global counter
        for _ in range(n):
            with lock:
                counter += 1

    ts = [threading.Thread(target=bump_locked) for _ in range(4)]
    for th in ts: th.start()
    for th in ts: th.join()
    print(f"  with lock: {counter}")
