"""
Problem 3 — Business Days Between Two Dates (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from datetime import date, timedelta


def is_business_day(d, holidays):
    """True when d is Mon–Fri and not in holidays."""
    # TODO
    raise NotImplementedError


def business_days_between(start, end, holidays=None):
    """
    Count business days in [start, end). Raise ValueError if end < start.
    """
    # TODO: treat None holidays as an empty set
    # TODO: reject end < start with ValueError
    # TODO: walk from start up to (but not including) end, counting business days
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
# ---------------------------------------------------------------------------
def run_tests():
    holidays = {
        date(2026, 1, 1),   # New Year's Day (Thu)
        date(2026, 7, 3),   # Independence Day observed (Fri)
    }

    # Mid-week stretch with no holiday: Mon..Thu counted, Fri excluded → 4
    assert business_days_between(date(2026, 1, 5), date(2026, 1, 9), holidays) == 4

    # Include start, exclude end, skip New Year's
    # [Dec 31, Jan 2): Dec 31 yes, Jan 1 holiday → 1
    assert business_days_between(date(2025, 12, 31), date(2026, 1, 2), holidays) == 1

    # [Dec 31, Jan 3): Dec 31, skip Jan 1, Jan 2 → 2
    assert business_days_between(date(2025, 12, 31), date(2026, 1, 3), holidays) == 2

    # Weekend inside the range is skipped
    # [Fri Jan 2, Mon Jan 5): Fri only (Sat/Sun skipped) → 1
    assert business_days_between(date(2026, 1, 2), date(2026, 1, 5), holidays) == 1

    # Full week across observed Independence Day
    # [Thu Jul 2, Mon Jul 6): Thu yes, Fri holiday, Sat/Sun skip → 1
    assert business_days_between(date(2026, 7, 2), date(2026, 7, 6), holidays) == 1

    # Empty range
    assert business_days_between(date(2026, 1, 5), date(2026, 1, 5), holidays) == 0

    # None holidays
    assert business_days_between(date(2026, 3, 6), date(2026, 3, 9), None) == 1  # Fri only

    # Invalid range
    try:
        business_days_between(date(2026, 1, 10), date(2026, 1, 5), holidays)
        assert False, "expected ValueError"
    except ValueError:
        pass

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
