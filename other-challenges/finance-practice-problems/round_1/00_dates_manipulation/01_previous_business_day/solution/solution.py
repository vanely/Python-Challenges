"""
Problem 1 — Previous Business Day (SOLUTION)

Walk one day at a time backward from the day before `d` until you land on
a weekday that is not in the holiday set.
"""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def is_business_day(d, holidays):
    """True when d is Mon–Fri and not in holidays."""
    # weekday(): 0=Mon ... 4=Fri, 5=Sat, 6=Sun
    return d.weekday() < 5 and d not in holidays


def previous_business_day(d, holidays=None):
    """
    Return the nearest business day strictly before d.
    """
    if holidays is None:
        holidays = set()

    # Always move at least one day back — we want the *previous* day,
    # even when d itself is already a business day.
    candidate = d - ONE_DAY
    while not is_business_day(candidate, holidays):
        candidate -= ONE_DAY
    return candidate


# ---------------------------------------------------------------------------
# Tests: run this file directly to check everything works.
# ---------------------------------------------------------------------------
def run_tests():
    holidays = {
        date(2026, 1, 1),   # New Year's Day (Thu)
        date(2026, 7, 3),   # Independence Day observed (Fri)
    }

    # Weekday whose previous day is also a weekday
    assert previous_business_day(date(2026, 1, 7), holidays) == date(2026, 1, 6)

    # Monday → previous Friday
    assert previous_business_day(date(2026, 1, 5), holidays) == date(2026, 1, 2)

    # Day after a Thursday holiday → Wednesday
    assert previous_business_day(date(2026, 1, 2), holidays) == date(2025, 12, 31)

    # Monday after a holiday Friday + weekend → Thursday
    # Jul 3 holiday, Jul 4 Sat, Jul 5 Sun → from Mon Jul 6 back to Thu Jul 2
    assert previous_business_day(date(2026, 7, 6), holidays) == date(2026, 7, 2)

    # No holidays provided (None) — weekend still skipped
    assert previous_business_day(date(2026, 3, 9), None) == date(2026, 3, 6)

    # Empty holiday set
    assert previous_business_day(date(2026, 3, 9), set()) == date(2026, 3, 6)

    # Helper sanity
    assert is_business_day(date(2026, 1, 2), holidays) is True
    assert is_business_day(date(2026, 1, 1), holidays) is False
    assert is_business_day(date(2026, 1, 3), holidays) is False  # Saturday
    assert is_business_day(date(2026, 1, 4), holidays) is False  # Sunday

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
