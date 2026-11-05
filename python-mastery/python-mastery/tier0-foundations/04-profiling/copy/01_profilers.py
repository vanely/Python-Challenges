"""0.4 — One slow program, profiled four ways.

    python 01_profilers.py            # runs the built-in demos (timeit, cProfile, tracemalloc)
    py-spy record -o flame.svg -- python 01_profilers.py --work-only   # sampling flamegraph
    py-spy top -- python 01_profilers.py --work-only
    scalene 01_profilers.py --- --work-only                            # line-level CPU+memory
    python -m cProfile -o out.prof 01_profilers.py --work-only && snakeviz out.prof
"""
import cProfile
import io
import pstats
import random
import sys
import timeit
import tracemalloc
from collections import Counter

random.seed(1)
WORDS = [f"w{i}" for i in range(2000)]


def make_docs(n: int) -> list[str]:
    return [" ".join(random.choices(WORDS, k=50)) for _ in range(n)]


# --- the slow code (deliberately) -------------------------------------------------------------
def tokenize(doc: str) -> list[str]:
    out = []
    for w in doc.split(" "):
        out.append(w.lower())
    return out


def is_stopword(w: str, stops: list[str]) -> bool:
    return w in stops                          # O(n) list membership in a hot loop


def count_words(docs: list[str], stops: list[str]) -> Counter[str]:
    c: Counter[str] = Counter()
    for d in docs:
        for w in tokenize(d):
            if not is_stopword(w, stops):
                c[w] += 1
    return c


def top_pairs(docs: list[str], k: int) -> list[tuple[tuple[str, str], int]]:
    pairs: Counter[tuple[str, str]] = Counter()
    for d in docs:
        toks = tokenize(d)
        for i in range(len(toks) - 1):
            pairs[(toks[i], toks[i + 1])] += 1
    return pairs.most_common(k)


def work() -> None:
    docs = make_docs(3000)
    stops = WORDS[:300]
    count_words(docs, stops)
    top_pairs(docs, 10)


# --- 1. timeit: micro-comparisons ---------------------------------------------------------------------
def demo_timeit() -> None:
    print("== timeit ==")
    stops_list = WORDS[:300]
    stops_set = set(stops_list)
    w = "w1999"
    for label, stmt in [
        ("list membership", lambda: w in stops_list),
        ("set membership ", lambda: w in stops_set),
    ]:
        best = min(timeit.repeat(stmt, number=100_000, repeat=5))
        print(f"  {label}: {best * 1e9 / 100_000:8.1f} ns/op   (min of 5 repeats)")


# --- 2. cProfile + pstats: function-level, deterministic ------------------------------------------------
def demo_cprofile() -> None:
    print("== cProfile (top by tottime) ==")
    prof = cProfile.Profile()
    prof.enable()
    work()
    prof.disable()
    s = io.StringIO()
    ps = pstats.Stats(prof, stream=s).sort_stats("tottime")
    ps.print_stats(6)
    print("\n".join(line for line in s.getvalue().splitlines() if line.strip())[:1500])
    print("  -- who calls is_stopword? --")
    s = io.StringIO()
    pstats.Stats(prof, stream=s).print_callers("is_stopword")
    print("\n".join(s.getvalue().splitlines()[-4:]))


# --- 3. tracemalloc: where memory is allocated -----------------------------------------------------------
def demo_tracemalloc() -> None:
    print("== tracemalloc (top allocation sites) ==")
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    docs = make_docs(2000)
    pairs = top_pairs(docs, 5)
    after = tracemalloc.take_snapshot()
    for stat in after.compare_to(before, "lineno")[:4]:
        print("  ", stat)
    cur, peak = tracemalloc.get_traced_memory()
    print(f"  current {cur / 1e6:.1f} MB, peak {peak / 1e6:.1f} MB")
    tracemalloc.stop()
    del docs, pairs


if __name__ == "__main__":
    if "--work-only" in sys.argv:
        work()
    else:
        demo_timeit()
        demo_cprofile()
        demo_tracemalloc()
