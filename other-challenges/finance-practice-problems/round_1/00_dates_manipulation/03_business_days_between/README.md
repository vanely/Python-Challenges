# Problem 3 — Business Days Between Two Dates

Interest accrual, SLA clocks, and "how many clearing days did this take?" all
need a count of business days in a range.

Write:

```python
business_days_between(start, end, holidays=None) -> int
```

Count how many business days fall in the **half-open** interval `[start, end)` —
include `start` if it is a business day, **exclude** `end`.

## Why half-open?

`[start, end)` is the usual choice in code: adjacent ranges don't double-count
a boundary day, and `start == end` naturally means `0`. Say this out loud in
the interview so they know you thought about inclusive vs exclusive.

## Example

```python
from datetime import date

holidays = {date(2026, 1, 1)}

# Wed Dec 31 → Fri Jan 2 (exclusive end): counts Dec 31 and skips Jan 1 → 1 day
business_days_between(date(2025, 12, 31), date(2026, 1, 2), holidays)  # -> 1

# Mon Jan 5 → Fri Jan 9: Mon Tue Wed Thu = 4 (Fri excluded)
business_days_between(date(2026, 1, 5), date(2026, 1, 9), holidays)    # -> 4

# Same day → 0
business_days_between(date(2026, 1, 5), date(2026, 1, 5), holidays)    # -> 0
```

## Rules

- If `end < start`, raise `ValueError`.
- `holidays` may be `None` (treat as empty set).
- Weekends never count. Holidays never count.

## Things to talk about

- Half-open vs fully inclusive: if they want both ends counted, that's
  `business_days_between(start, end + one_day)`.
- For long ranges, day-by-day is O(days). A closed formula (or a lookup table
  of cumulative business days) is better at scale — mention it, then ship the
  clear loop unless they ask for more.
