# Problem 1 — Transaction Summary

You receive a day's worth of transactions as a list of dictionaries, **in the order they happened**:

```python
transactions = [
    {"id": "t1", "account": "A100", "type": "deposit",    "amount": "500.00"},
    {"id": "t2", "account": "A100", "type": "withdrawal", "amount": "120.50"},
    {"id": "t2", "account": "A100", "type": "withdrawal", "amount": "120.50"},  # duplicate!
    {"id": "t3", "account": "B200", "type": "withdrawal", "amount": "10.00"},   # overdraft!
]
```

Every account starts at a balance of `0.00`. Amounts arrive as **strings**.

Write `summarize_transactions(transactions)` and return a dictionary with three keys:

- `"balances"`: `{account: Decimal balance}` for every account that appears.
- `"duplicate_ids"`: ids seen more than once, in the order the repeats appeared. Process only the **first** copy of each id.
- `"rejected_ids"`: transactions that were **not applied**. These are:
  - withdrawals that would make the balance go below zero (overdrafts)
  - amounts that are zero or negative
  - amounts that aren't a valid number (e.g. `"abc"`)
  - an unknown `type`

## Example

For the list above:

```python
{
    "balances": {"A100": Decimal("379.50"), "B200": Decimal("0.00")},
    "duplicate_ids": ["t2"],
    "rejected_ids": ["t3"],
}
```

## Things to talk about

- Why `Decimal` and not `float`?
- Why do duplicates happen in real systems? (Retries, or a vendor resending a file.)
- What would you change if the list had 50 million rows? (Stream through it instead of loading it all; push the work into SQL.)
