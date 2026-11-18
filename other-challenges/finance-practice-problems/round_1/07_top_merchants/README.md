# Problem 7 — Top K Merchants

Given a customer's card transactions, find their **top `k` merchants**.

```python
transactions = [
    {"merchant": "Starbucks", "amount": "5.75"},
    {"merchant": "Shell",     "amount": "40.00"},
    {"merchant": "Starbucks", "amount": "6.10"},
    {"merchant": "Amazon",    "amount": "89.99"},
    {"merchant": "Shell",     "amount": "38.20"},
    {"merchant": "Starbucks", "amount": "4.95"},
]
```

## Part A: `top_merchants_by_count(transactions, k)`

Return a list of `(merchant, count)` pairs, most visits first.
**Break ties alphabetically** so the output is always the same.

```python
top_merchants_by_count(transactions, 2)
# -> [("Starbucks", 3), ("Shell", 2)]
```

## Part B: `top_merchants_by_spend(transactions, k)`

Same idea, but rank by **total dollars spent** (a `Decimal`). Break ties alphabetically.

```python
top_merchants_by_spend(transactions, 2)
# -> [("Amazon", Decimal("89.99")), ("Shell", Decimal("78.20"))]
```

## Rules

- Treat merchant names as the same regardless of case and surrounding spaces (`" starbucks "` = `"Starbucks"`). Output the version you saw first.
- If `k` is bigger than the number of merchants, return them all.
- `k <= 0` returns an empty list.

## Things to talk about

- `collections.Counter` does Part A in one line, but `most_common()` doesn't break ties alphabetically. You have to sort yourself.
- Sorting is O(m log m) for m merchants. With millions of merchants and a small k, `heapq.nsmallest(k, ...)` is O(m log k).
- In real data, merchant names are messy ("AMZN Mktp US*2K4"). Cleaning them up is a whole problem of its own.
