"""Day 11 — polars essentials."""
import io

import polars as pl

csv = """order_id,customer,item,qty,price,placed_at
1,ada,widget,2,9.50,2026-09-01
2,ada,gizmo,1,24.00,2026-09-01
3,grace,widget,5,9.50,2026-09-02
4,linus,gizmo,3,24.00,2026-09-03
5,grace,doohickey,1,3.25,2026-09-03
"""
df = pl.read_csv(io.StringIO(csv), try_parse_dates=True)
print(df.schema)
print(df.head(3))

# select / with_columns / filter — expressions, not row loops
df = df.with_columns(total=pl.col("qty") * pl.col("price"))
big = df.filter(pl.col("total") > 20).select("order_id", "customer", "total")
print(big)

# group_by / agg
by_customer = (
    df.group_by("customer")
    .agg(
        orders=pl.len(),
        revenue=pl.col("total").sum(),
        avg_qty=pl.col("qty").mean(),
        items=pl.col("item").unique().sort(),
    )
    .sort("revenue", descending=True)
)
print(by_customer)

# dates and strings
print(
    df.with_columns(
        day=pl.col("placed_at").dt.day(),
        item_upper=pl.col("item").str.to_uppercase(),
        is_widget=pl.col("item") == "widget",
    ).select("order_id", "day", "item_upper", "is_widget")
)

# join
customers = pl.DataFrame({"customer": ["ada", "grace", "linus"], "tier": ["gold", "silver", "gold"]})
print(df.join(customers, on="customer", how="left").group_by("tier").agg(pl.col("total").sum()))

# lazy: build a plan, optimise, execute once
plan = (
    df.lazy()
    .filter(pl.col("qty") >= 2)
    .group_by("item")
    .agg(pl.col("total").sum().alias("rev"))
    .sort("rev", descending=True)
)
print(plan.explain())
print(plan.collect())

# to/from Python
rows = df.to_dicts()                   # list[dict] — hand to Pydantic/JSON
print(rows[0])
print(pl.DataFrame(rows).shape)
df.write_csv("_out.csv")
import os
os.remove("_out.csv")
