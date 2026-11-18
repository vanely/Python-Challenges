# Problem 2 — Add Business Days (ACH T+N)

ACH credits often settle in **T+1** or **T+2** business days. Wires and loan
funding windows use the same idea: skip weekends and holidays, count only
good banking days.

Write:

```python
add_business_days(d, n, holidays=None) -> date
```

Move `n` business days away from `d` and return the landing date.

## Rules

- `n > 0` → walk **forward**, counting only business days.
- `n < 0` → walk **backward**, counting only business days.
- `n == 0` → return `d` **unchanged**, even if `d` is a weekend or holiday.
  (Zero steps means "don't move.")
- The starting day `d` itself is **not** counted. You begin counting after you
  take the first step — same idea as "two business days from Friday" landing
  on Tuesday, not Monday.
- `holidays` may be `None` (treat as empty set).

## Example

```python
from datetime import date

holidays = {date(2026, 1, 1)}

# Friday + 1 business day → Monday (skip weekend)
add_business_days(date(2026, 1, 2), 1, holidays)   # -> date(2026, 1, 5)

# Friday + 2 business days → Tuesday
add_business_days(date(2026, 1, 2), 2, holidays)   # -> date(2026, 1, 6)

# Wednesday Dec 31 + 1 → skip New Year's (Thu) → Friday Jan 2
add_business_days(date(2025, 12, 31), 1, holidays) # -> date(2026, 1, 2)

# Monday - 1 business day → previous Friday
add_business_days(date(2026, 1, 5), -1, holidays)  # -> date(2026, 1, 2)

# Zero steps: leave a Saturday alone
add_business_days(date(2026, 1, 3), 0, holidays)   # -> date(2026, 1, 3)
```

## Things to talk about

- This is the same loop as previous/next business day, just repeated `abs(n)` times.
- In production you'd often use a pre-built business-day calendar (or a library)
  instead of scanning day-by-day — but the interview wants the clear loop.
- Clarify T+0 vs T+1 with the interviewer: does "same day" count if it's already
  a business day? Here `n == 0` means literally don't move.
