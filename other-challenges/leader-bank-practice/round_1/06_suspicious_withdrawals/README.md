# Problem 6 — Flag Suspicious Withdrawal Activity

A fraud rule: **flag any account with more than `max_count` withdrawals inside any 24-hour window.**

You get a list of `(account_id, timestamp)` pairs, where `timestamp` is a `datetime`. The list is **not sorted**. Write:

```python
flag_suspicious_accounts(withdrawals, max_count, window=timedelta(hours=24))
```

Return a **sorted list** of the account ids to flag.

## What "inside a 24-hour window" means

A group of withdrawals counts as one window when the newest minus the oldest is **less than** 24 hours. So withdrawals at 9:00 Monday and 9:00 Tuesday (exactly 24 hours apart) are **not** in the same window.

## Example

```python
from datetime import datetime as dt

withdrawals = [
    ("A1", dt(2026, 11, 2, 9, 0)),
    ("A1", dt(2026, 11, 2, 13, 0)),
    ("A1", dt(2026, 11, 2, 22, 0)),
    ("A1", dt(2026, 11, 2, 23, 30)),   # A1 now has 4 in under 24h
    ("B2", dt(2026, 11, 1, 9, 0)),
    ("B2", dt(2026, 11, 2, 10, 0)),
    ("B2", dt(2026, 11, 3, 11, 0)),
    ("B2", dt(2026, 11, 4, 12, 0)),    # B2 has 4 total, but spread over days
]

flag_suspicious_accounts(withdrawals, max_count=3)   # -> ["A1"]
```

## The approach to aim for: a sliding window

1. Group timestamps by account, then sort each account's times.
2. Walk through the times, keeping a `collections.deque` of times in the current window.
3. Add each new time on the right. Remove old times from the left while they're 24h or more older than the newest.
4. If the deque ever holds more than `max_count` times, flag the account.

Each timestamp is added and removed at most once, so the walk is **O(n)** after sorting.

## Things to talk about

- The simple approach (check every pair) is O(n²). Explain why the window is better.
- In production, this rule would run as events stream in, not as one big list. Per account, you'd keep the same deque (or use Redis or a streaming tool).
