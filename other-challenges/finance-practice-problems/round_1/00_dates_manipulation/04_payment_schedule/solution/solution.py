"""
Problem 4 — Monthly Payment Schedule (SOLUTION)

1. Shift the anchor month-by-month (clamp day-of-month when needed).
2. Apply the "following" convention: push weekend/holiday dates forward.
3. Build the schedule from those two helpers so month-end series stay pinned.
"""

import calendar
from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def is_business_day(d, holidays):
    """True when d is Mon–Fri and not in holidays."""
    return d.weekday() < 5 and d not in holidays


def add_months(d, months):
    """
    Shift d by `months` calendar months. Clamp the day if the target month
    is shorter (e.g. Jan 31 + 1 month → Feb 28/29).
    """
    # Convert to a 0-based month index, add, then convert back.
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1

    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


def adjust_following(d, holidays):
    """If d is not a business day, walk forward until it is."""
    while not is_business_day(d, holidays):
        d += ONE_DAY
    return d


def build_payment_dates(first, months, holidays=None):
    """
    Return `months` due dates starting at `first`, each adjusted with the
    following business-day convention.
    """
    if holidays is None:
        holidays = set()

    if months < 0:
        raise ValueError(f"months must be >= 0, got {months}")

    dates = []
    for i in range(months):
        raw = add_months(first, i)
        dates.append(adjust_following(raw, holidays))
    return dates


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    holidays = {
        date(2026, 1, 1),   # New Year's Day (Thu)
        date(2026, 7, 3),   # Independence Day observed (Fri)
    }

    # --- add_months ---
    assert add_months(date(2026, 1, 15), 1) == date(2026, 2, 15)
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)  # clamp
    assert add_months(date(2026, 1, 31), 2) == date(2026, 3, 31)
    assert add_months(date(2026, 1, 15), 0) == date(2026, 1, 15)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)  # leap year

    # --- adjust_following ---
    assert adjust_following(date(2026, 1, 12), holidays) == date(2026, 1, 12)
    assert adjust_following(date(2026, 1, 3), holidays) == date(2026, 1, 5)   # Sat → Mon
    assert adjust_following(date(2026, 1, 1), holidays) == date(2026, 1, 2)   # holiday → Fri
    assert adjust_following(date(2026, 7, 3), holidays) == date(2026, 7, 6)   # hol+weekend

    # --- build_payment_dates ---
    # Jan 12 Mon / Feb 12 Thu / Mar 12 Thu — all already business days
    assert build_payment_dates(date(2026, 1, 12), 3, holidays) == [
        date(2026, 1, 12),
        date(2026, 2, 12),
        date(2026, 3, 12),
    ]

    # First due date is a Saturday → push to Monday; later months fine
    assert build_payment_dates(date(2026, 1, 3), 3, holidays) == [
        date(2026, 1, 5),
        date(2026, 2, 3),
        date(2026, 3, 3),
    ]

    # Month-end anchor: adjust after clamping, don't drift the series
    # Jan 31 Sat → Feb 2; Feb 28 Sat → Mar 2; Mar 31 Tue → Mar 31
    assert build_payment_dates(date(2026, 1, 31), 3, holidays) == [
        date(2026, 2, 2),
        date(2026, 3, 2),
        date(2026, 3, 31),
    ]

    # Holiday on the raw due date
    assert build_payment_dates(date(2026, 7, 3), 2, holidays) == [
        date(2026, 7, 6),
        date(2026, 8, 3),
    ]

    assert build_payment_dates(date(2026, 1, 12), 0, holidays) == []
    assert build_payment_dates(date(2026, 1, 12), 1, None) == [date(2026, 1, 12)]

    try:
        build_payment_dates(date(2026, 1, 12), -1, holidays)
        assert False, "expected ValueError"
    except ValueError:
        pass

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
