"""v1 must match v0 on every field except rank (ties may differ)."""

from __future__ import annotations

import os
from pathlib import Path

import gen
import v0_baseline
import v1_algorithmic

_REFERENCE = Path(__file__).resolve().parents[1] / "reference" / "v1_algorithmic.py"


def test_v1_is_yours() -> None:
    if os.environ.get("CHECK_REFERENCE") == "1":
        return
    assert Path(v1_algorithmic.__file__).resolve() != _REFERENCE, (
        "write v1_algorithmic.py in the lab folder; reference/ is not your solution"
    )


def _norm(result: dict[str, dict[str, float | int]]) -> dict[str, tuple[object, ...]]:
    return {
        key: (
            row["status"],
            row["endpoint_len"],
            row["count"],
            round(float(row["mean"]), 3),
            row["p95"],
            row["unique_users"],
        )
        for key, row in result.items()
    }


def test_v1_matches_baseline(tmp_path: Path) -> None:
    log = tmp_path / "access.log"
    gen.main(300, str(log))
    assert _norm(v1_algorithmic.analyse(str(log))) == _norm(v0_baseline.analyse(str(log)))
