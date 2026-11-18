# Problem 1 — Previous Business Day

Banks often need "the last good day before this one" — for example, pricing as-of
yesterday, or finding the prior settlement date when today is a holiday.

Write:

```python
previous_business_day(d, holidays=None) -> date
```

Return the nearest date **strictly before** `d` that is a business day.

A business day is a Monday–Friday that is **not** in `holidays` (a `set` of
`datetime.date`, default empty).

## Example

```python
from datetime import date

holidays = {date(2026, 1, 1)}  # New Year's Day (Thursday)

previous_business_day(date(2026, 1, 2), holidays)
# -> date(2025, 12, 31)
# Jan 1 is a holiday, so we keep walking back to Wednesday Dec 31.

previous_business_day(date(2026, 1, 5), holidays)
# -> date(2026, 1, 2)
# Monday → skip Sun/Sat → Friday Jan 2.
```

## Rules

- Always step at least one day back. Even if `d` itself is a business day, you
  want the **previous** one.
- `holidays` may be `None` — treat that like an empty set.
- You will not be asked for a date so early that you run out of calendar; assume
  a normal modern date.

## Things to talk about

- Why a `set` for holidays? Membership must stay cheap if the calendar is large.
- Observed holidays: July 4 on a Saturday is often observed the Friday before.
  Your function doesn't invent that — the caller puts the observed date in the set.
- Follow-up they might ask: `next_business_day` is the same loop, walking forward.
