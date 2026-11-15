# Problem 5 — Merge Overlapping Rate-Lock Periods

When a borrower **locks** a mortgage rate, the bank guarantees that rate for a stretch of days. A loan officer may extend or re-lock, so one loan can end up with several lock periods that overlap.

You get a list of `(start_date, end_date)` pairs (inclusive, `datetime.date` objects), in **any order**. Write `merge_lock_periods(periods)` that returns the merged periods, sorted by start date.

**Two periods merge if they overlap OR touch.** If one ends on the 10th and the next starts on the 11th, there was no gap in coverage, so treat them as one period.

## Example

```python
from datetime import date as d

merge_lock_periods([
    (d(2026, 3, 20), d(2026, 4, 5)),
    (d(2026, 3, 1),  d(2026, 3, 15)),
    (d(2026, 3, 10), d(2026, 3, 25)),   # overlaps both of the above
    (d(2026, 5, 1),  d(2026, 5, 30)),   # separate
])
# -> [(d(2026, 3, 1), d(2026, 4, 5)), (d(2026, 5, 1), d(2026, 5, 30))]
```

## Rules

- An empty list returns an empty list.
- A period whose end is before its start is invalid: raise `ValueError`.
- Don't change the caller's list (sort a copy).

## Things to talk about

- Time is **O(n log n)** because of the sort. The merge itself is a single O(n) pass.
- Follow-up they might ask: "Find the gaps when the loan was *not* locked." That's the space between the merged periods.
