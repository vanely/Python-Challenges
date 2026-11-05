"""Drop into the perflab next to bench.py once `maturin develop --release` has run."""
import sys

import logparse_rs


def analyse(path: str) -> dict[str, dict[str, float | int]]:
    return logparse_rs.aggregate(path)


if __name__ == "__main__":
    out = analyse(sys.argv[1] if len(sys.argv) > 1 else "access.log")
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["rank"])[:10]:
        print(k, v)
