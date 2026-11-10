"""v3 — Cython parse loop + v1-style aggregation. Requires `python setup.py build_ext --inplace`."""
import sys

from v3_parse import aggregate  # type: ignore[import-not-found]


def analyse(path: str) -> dict[str, dict[str, float | int]]:
    agg = aggregate(path)
    latencies: dict[tuple[int, str], list[int]] = agg["latencies"]
    users: dict[tuple[int, str], set[str]] = agg["users"]
    ranked = sorted(latencies, key=lambda k: -len(latencies[k]))
    rank_of = {k: i + 1 for i, k in enumerate(ranked)}
    result: dict[str, dict[str, float | int]] = {}
    for key, lats in latencies.items():
        lats.sort()
        status, ep = key
        result[f"{status}|{ep}"] = {
            "status": status,
            "endpoint_len": len(ep),
            "count": len(lats),
            "mean": sum(lats) / len(lats),
            "p95": lats[int(0.95 * (len(lats) - 1))],
            "unique_users": len(users[key]),
            "rank": rank_of[key],
        }
    return result


if __name__ == "__main__":
    out = analyse(sys.argv[1] if len(sys.argv) > 1 else "access.log")
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["rank"])[:10]:
        print(k, v)
