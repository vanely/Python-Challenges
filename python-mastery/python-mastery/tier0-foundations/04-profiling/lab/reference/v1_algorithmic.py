"""v1 — same output, pure Python, algorithmic fixes only."""
import sys
from collections import defaultdict

_PREFIX_LEN = len("user=")


def parse(line: str) -> tuple[int, str, str, int]:
    # str.split beats regex here: fixed format, no backtracking, no match-object allocation
    _ts, status, ep, user, lat = line.split(" ")
    return int(status), ep, user[_PREFIX_LEN:], int(lat[11:])          # "latency_ms=" is 11 chars


def p95(values: list[int]) -> int:
    # still O(n log n) per key but on far fewer, and no copying of the original
    values.sort()
    return values[int(0.95 * (len(values) - 1))]


def analyse(path: str) -> dict[str, dict[str, float | int]]:
    latencies: defaultdict[tuple[int, str], list[int]] = defaultdict(list)
    users: defaultdict[tuple[int, str], set[str]] = defaultdict(set)   # O(1) membership
    with open(path, encoding="utf-8") as f:
        for line in f:
            status, ep, user, lat = parse(line)
            key = (status, ep)                                          # tuple key, no string build
            latencies[key].append(lat)
            users[key].add(user)
    # rank once, not per key
    ranked = sorted(latencies, key=lambda k: -len(latencies[k]))
    rank_of = {k: i + 1 for i, k in enumerate(ranked)}
    result: dict[str, dict[str, float | int]] = {}
    for key, lats in latencies.items():
        status, ep = key
        result[f"{status}|{ep}"] = {
            "status": status,
            "endpoint_len": len(ep),
            "count": len(lats),
            "mean": sum(lats) / len(lats),
            "p95": p95(lats),
            "unique_users": len(users[key]),
            "rank": rank_of[key],
        }
    return result


if __name__ == "__main__":
    out = analyse(sys.argv[1] if len(sys.argv) > 1 else "access.log")
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["rank"])[:10]:
        print(k, v)
