from pathlib import Path

import logparse_rs


def test_aggregate(tmp_path: Path) -> None:
    p = tmp_path / "a.log"
    p.write_text(
        "2026-09-01T00:00:00+00:00 200 /a user=u1 latency_ms=10\n"
        "2026-09-01T00:00:01+00:00 200 /a user=u2 latency_ms=30\n"
        "2026-09-01T00:00:02+00:00 500 /b user=u1 latency_ms=5\n"
    )
    out = logparse_rs.aggregate(str(p))
    assert out["200|/a"] == {"status": 200, "endpoint_len": 2, "count": 2, "mean": 20.0, "p95": 10, "unique_users": 2, "rank": 1}
    assert out["500|/b"]["rank"] == 2
