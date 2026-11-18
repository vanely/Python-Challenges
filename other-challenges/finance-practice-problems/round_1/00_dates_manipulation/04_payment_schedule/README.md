# Problem 4 — Monthly Payment Schedule (Following Convention)

Loan and autopay systems generate a list of due dates: the same day of the
month, every month, for N months. If a due date lands on a weekend or holiday,
banks usually push it **forward** to the next business day. That rule is called
the **following** business-day convention.

Write:

```python
add_months(d, months) -> date
adjust_following(d, holidays) -> date
build_payment_dates(first, months, holidays=None) -> list[date]
```

## What each function does

### `add_months(d, months)`

Return the date that is `months` calendar months after `d`, **keeping the day
of month when possible**. If that day doesn't exist (Jan 31 + 1 month), clamp
to the last day of the target month (Feb 28/29).

Stdlib hint: `calendar.monthrange(year, month)[1]` is the last day of that month.

### `adjust_following(d, holidays)`

If `d` is already a business day, return it. Otherwise walk **forward** one day
at a time until you hit a business day.

### `build_payment_dates(first, months, holidays=None)`

For `i` in `0 .. months-1`:

1. `raw = add_months(first, i)`
2. append `adjust_following(raw, holidays)`

So the unadjusted anchor is always "the Nth month after `first`," and only then
do you apply the following convention. That way a January 31 schedule stays
pinned to month-end rather than drifting after a push-forward.

## Example

```python
from datetime import date

holidays = {date(2026, 1, 1), date(2026, 7, 3)}

build_payment_dates(date(2026, 1, 12), 3, holidays)
# -> [date(2026, 1, 12), date(2026, 2, 12), date(2026, 3, 12)]

build_payment_dates(date(2026, 1, 3), 3, holidays)
# Jan 3 is Saturday → Mon Jan 5; Feb 3 and Mar 3 are already weekdays
# -> [date(2026, 1, 5), date(2026, 2, 3), date(2026, 3, 3)]
```

## Rules

- `months == 0` → return `[]`.
- `months < 0` → raise `ValueError`.
- `holidays` may be `None` (treat as empty set).

## Things to talk about

- **Following** vs **preceding** vs **modified following**: modified following
  also pushes forward, but if that lands in the *next* month it snaps back to
  the previous business day instead — common in fixed-income.
- Why adjust *after* adding months? The **anchors** stay on the original
  day-of-month (Jan 31 → Feb 28 → Mar 31). If you adjusted first
  (Jan 31 Sat → Feb 2) and then added months from Feb 2, you'd drift to
  Feb 2 / Mar 2 / Apr 2 and lose the month-end intent. Adjustment still
  may push an individual due date into the next month — that's expected
  with plain following.
