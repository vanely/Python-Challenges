"""v2 — polars: one lazy plan; parsing and aggregation happen in native code."""
import sys

import polars as pl


def analyse(path: str) -> dict[str, dict[str, float | int]]:
    lf = (
        pl.scan_csv(path, has_header=False, separator=" ", new_columns=["ts", "status", "ep", "user", "lat"])
        .with_columns(
            pl.col("user").str.strip_prefix("user="),
            pl.col("lat").str.strip_prefix("latency_ms=").cast(pl.Int64),
        )
        .group_by("status", "ep")
        .agg(
            count=pl.len(),
            mean=pl.col("lat").mean(),
            p95=pl.col("lat").quantile(0.95, interpolation="lower"),
            unique_users=pl.col("user").n_unique(),
        )
        .with_columns(rank=pl.col("count").rank(method="ordinal", descending=True))
    )
    df = lf.collect()
    return {
        f"{r['status']}|{r['ep']}": {
            "status": r["status"],
            "endpoint_len": len(r["ep"]),
            "count": r["count"],
            "mean": r["mean"],
            "p95": r["p95"],
            "unique_users": r["unique_users"],
            "rank": r["rank"],
        }
        for r in df.to_dicts()
    }


if __name__ == "__main__":
    out = analyse(sys.argv[1] if len(sys.argv) > 1 else "access.log")
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["rank"])[:10]:
        print(k, v)
