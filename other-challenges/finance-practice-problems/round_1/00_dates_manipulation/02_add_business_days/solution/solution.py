"""
Problem 2 — Add Business Days (SOLUTION)

Step one calendar day at a time in the chosen direction. Only count a step
when the day you land on is a business day. Repeat until you've counted
abs(n) of them.
"""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def is_business_day(d, holidays):
    """True when d is Mon–Fri and not in holidays."""
    return d.weekday() < 5 and d not in holidays


def add_business_days(d, n, holidays=None):
    """
    Move n business days from d. Positive = forward, negative = backward,
    zero = return d unchanged.
    """
    if holidays is None:
        holidays = set()

    # Zero steps means do not move — even if d is a weekend or holiday.
    if n == 0:
        return d

    step = ONE_DAY if n > 0 else -ONE_DAY
    remaining = abs(n)
    current = d

    while remaining > 0:
        current = current + step
        if is_business_day(current, holidays):
            remaining -= 1

    return current


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    holidays = {
        date(2026, 1, 1),   # New Year's Day (Thu)
        date(2026, 7, 3),   # Independence Day observed (Fri)
    }

    # Friday + 1 → Monday
    assert add_business_days(date(2026, 1, 2), 1, holidays) == date(2026, 1, 5)

    # Friday + 2 → Tuesday
    assert add_business_days(date(2026, 1, 2), 2, holidays) == date(2026, 1, 6)

    # Skip a mid-week holiday
    assert add_business_days(date(2025, 12, 31), 1, holidays) == date(2026, 1, 2)

    # Holiday Friday + weekend: Thu Jul 2 + 1 → Mon Jul 6
    assert add_business_days(date(2026, 7, 2), 1, holidays) == date(2026, 7, 6)

    # Negative: Monday - 1 → Friday
    assert add_business_days(date(2026, 1, 5), -1, holidays) == date(2026, 1, 2)

    # Negative across a holiday
    assert add_business_days(date(2026, 1, 2), -1, holidays) == date(2025, 12, 31)

    # Zero leaves the date alone, even on a weekend
    assert add_business_days(date(2026, 1, 3), 0, holidays) == date(2026, 1, 3)
    assert add_business_days(date(2026, 1, 1), 0, holidays) == date(2026, 1, 1)

    # None holidays — weekends still skipped
    assert add_business_days(date(2026, 3, 6), 1, None) == date(2026, 3, 9)

    # Larger hop
    assert add_business_days(date(2026, 1, 2), 5, holidays) == date(2026, 1, 9)

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
