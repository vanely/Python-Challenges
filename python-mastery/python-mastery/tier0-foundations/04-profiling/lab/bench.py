"""Run every version on the same log, verify identical results, print a table.
    python bench.py access.log
"""
import importlib
import sys
import time

VERSIONS = ["v0_baseline", "v1_algorithmic", "v2_vectorised", "v3_cython"]


def normalise(d: dict[str, dict[str, float | int]]) -> dict[str, tuple[object, ...]]:
    return {
        k: (v["status"], v["count"], round(float(v["mean"]), 3), v["p95"], v["unique_users"], v["rank"])
        for k, v in d.items()
    }


def main(path: str) -> None:
    baseline = None
    rows = []
    mods = {}
    for name in VERSIONS:                       # import first: polars alone costs ~1s to import
        try:
            mods[name] = importlib.import_module(name)
        except ImportError as e:
            rows.append((name, None, f"skipped: {e}"))
    for name, mod in mods.items():
        t0 = time.perf_counter()
        out = normalise(mod.analyse(path))
        dt = time.perf_counter() - t0
        if baseline is None:
            baseline = out
            base_t = dt
        # rank ties can differ between implementations; compare everything but rank strictly
        same = {k: v[:-1] for k, v in out.items()} == {k: v[:-1] for k, v in baseline.items()}
        rows.append((name, dt, "OK" if same else "MISMATCH"))
    print(f"{'version':<16}{'seconds':>10}{'speedup':>10}  check")
    for name, dt, status in rows:
        if dt is None:
            print(f"{name:<16}{'-':>10}{'-':>10}  {status}")
        else:
            print(f"{name:<16}{dt:>10.2f}{base_t / dt:>9.1f}x  {status}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "access.log")
