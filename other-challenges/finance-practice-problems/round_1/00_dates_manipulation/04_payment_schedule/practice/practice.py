"""
Problem 4 — Monthly Payment Schedule (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

import calendar
from datetime import date, timedelta


def is_business_day(d, holidays):
    """True when d is Mon–Fri and not in holidays."""
    # TODO
    raise NotImplementedError


def add_months(d, months):
    """
    Shift d by `months` calendar months. Clamp the day if the target month
    is shorter (e.g. Jan 31 + 1 month → Feb 28/29).
    Hint: calendar.monthrange(year, month)[1] is the last day of that month.
    """
    # TODO
    raise NotImplementedError


def adjust_following(d, holidays):
    """If d is not a business day, walk forward until it is."""
    # TODO
    raise NotImplementedError


def build_payment_dates(first, months, holidays=None):
    """
    Return `months` due dates starting at `first`, each adjusted with the
    following business-day convention.
    """
    # TODO: treat None holidays as an empty set
    # TODO: raise ValueError if months < 0
    # TODO: for i in range(months): adjust_following(add_months(first, i), ...)
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
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
