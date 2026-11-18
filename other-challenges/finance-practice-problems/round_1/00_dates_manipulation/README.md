# Dates Manipulation — Business-Day Practice Set

Four short problems about banking calendars: weekends and holidays don't count as
business days. Each is sized for a 15–25 minute interview slice.

Banks care about this constantly — ACH settlement, wire cutoff, payment due dates,
and interest accrual all skip non-business days.

## Folder layout

```
00_dates_manipulation/
  01_previous_business_day/
    README.md            <- the problem description (read this first)
    practice/practice.py <- starter code: YOU fill in the functions
    solution/solution.py <- a worked, commented solution
  02_add_business_days/
  03_business_days_between/
  04_payment_schedule/
```

## How to practice

1. Read the problem's `README.md`.
2. Set a timer for 20 minutes.
3. Open `practice/practice.py` and fill in every spot marked `TODO`.
4. Run it. The tests at the bottom tell you what passes:

   ```bash
   python3 round_1/00_dates_manipulation/01_previous_business_day/practice/practice.py
   ```

5. Only then open `solution/solution.py` and compare.

Every file runs on its own, with no installs needed (standard library only —
`datetime`, plus `calendar` in the payment-schedule problem).

## Shared idea across all four

A **business day** is a weekday (Mon–Fri) that is **not** in the holiday set you
are given. Weekends never count as business days; the holiday set is only
consulted for weekdays.

```python
from datetime import date

def is_business_day(d, holidays):
    return d.weekday() < 5 and d not in holidays
```

`date.weekday()` returns `0` for Monday through `6` for Sunday, so `>= 5` means weekend.

## The problems

| # | Folder | Skill it practices |
|---|--------|--------------------|
| 1 | `01_previous_business_day` | walk a calendar backward; weekend + holiday skips |
| 2 | `02_add_business_days` | move N business days forward/back (ACH T+N) |
| 3 | `03_business_days_between` | count business days in a half-open range |
| 4 | `04_payment_schedule` | monthly dates + "following" business-day adjust |

## Habits to show the interviewer (say these out loud)

- Restate: "Business day means weekday and not in the holiday set."
- Ask whether the start date itself counts, and whether the range is inclusive.
- Prefer `datetime.date` over strings. Parse once at the boundary.
- Holidays as a `set` so membership checks are O(1).
- Edge cases: Monday after a holiday weekend, month-end pinning (Jan 31 + 1 month), `n == 0`.
