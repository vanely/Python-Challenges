"""Generate a synthetic access log. python gen.py [n_lines] [path]"""
import random
import sys
from datetime import UTC, datetime, timedelta

ENDPOINTS = ["/api/users", "/api/orders", "/api/items", "/health", "/login", "/logout"] + [
    f"/api/reports/{i}" for i in range(40)
]
STATUSES = [200] * 80 + [201] * 5 + [400] * 5 + [404] * 5 + [500] * 3 + [503] * 2


def main(n: int, path: str) -> None:
    random.seed(7)
    t = datetime(2026, 9, 1, tzinfo=UTC)
    with open(path, "w", encoding="utf-8") as f:
        for _ in range(n):
            t += timedelta(milliseconds=random.randint(1, 300))
            ep = random.choice(ENDPOINTS)
            st = random.choice(STATUSES)
            user = f"u{random.randint(1, 5000)}"
            lat = max(1, int(random.lognormvariate(4, 0.8)))
            f.write(f"{t.isoformat()} {st} {ep} user={user} latency_ms={lat}\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 500_000, sys.argv[2] if len(sys.argv) > 2 else "access.log")
