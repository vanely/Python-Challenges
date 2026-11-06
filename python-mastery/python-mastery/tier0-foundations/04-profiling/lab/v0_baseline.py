"""Deliberately slow baseline. Do not 'fix' this file; write v1..v3 instead."""
import re
import sys
from datetime import datetime


def parse(line: str) -> tuple[str, int, str, str, int]:
    m = re.match(r"(\S+) (\d+) (\S+) user=(\S+) latency_ms=(\d+)", line)   # re cache lookup per call
    assert m
    ts = datetime.fromisoformat(m.group(1))                                # full parse, unused precision
    return ts.strftime("%Y-%m-%d"), int(m.group(2)), m.group(3), m.group(4), int(m.group(5))


def analyse(path: str) -> dict[str, dict[str, float | int]]:
    latencies: dict[str, list[int]] = {}
    users: dict[str, list[str]] = {}
    for line in open(path, encoding="utf-8"):
        _day, status, ep, user, lat = parse(line)
        key = f"{status}|{ep}"
        latencies.setdefault(key, []).append(lat)
        ul = users.setdefault(key, [])
        if user not in ul:                                                   # O(n) membership
            ul.append(user)
    result: dict[str, dict[str, float | int]] = {}
    for key, lats in latencies.items():
        s = sorted(lats)                                                     # full sort per key
        status, ep = key.split("|")
        result[key] = {
            "status": int(status),
            "endpoint_len": len(ep),
            "count": len(lats),
            "mean": sum(lats) / len(lats),
            "p95": s[int(0.95 * (len(s) - 1))],
            "unique_users": len(users[key]),
            "rank": rank(latencies, key),
        }
    return result


def rank(latencies: dict[str, list[int]], key: str) -> int:
    ordered = sorted(latencies, key=lambda k: -len(latencies[k]))           # re-sorted per call
    return ordered.index(key) + 1


if __name__ == "__main__":
    out = analyse(sys.argv[1] if len(sys.argv) > 1 else "access.log")
    top = sorted(out.items(), key=lambda kv: kv[1]["rank"])[:10]
    for k, v in top:
        print(k, v)
