"""
Problem 1 — Previous Business Day (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from datetime import date, datetime, timedelta


def is_business_day(d, holidays):
    """
    True when d is Mon–Fri and not in holidays.
    Hint: d.weekday() is 0=Mon ... 6=Sun, so weekends are weekday() >= 5.
    """
    return d.weekday() < 5 and d not in holidays

def previous_business_day(d, holidays=None):
    """
    Return the nearest business day strictly before d.
    """
    if holidays is None:
        holidays = set()

    separated_date = str(d).split("-")
    previous_date = date(int(separated_date[0]), int(separated_date[1]), int(separated_date[2])) - timedelta(days=1)

    if is_business_day(previous_date, holidays):
        return previous_date

    return previous_business_day(previous_date, holidays)

# def previous_business_day(d, holidays=None):
#     """
#     Return the nearest business day strictly before d.
#     """
#     if not holidays:
#         holidays = set()

#     ONE_DAY = timedelta(days=1) 
#     possible_previous_day = d - ONE_DAY

#     while not is_business_day(possible_previous_day, holidays):
#        possible_previous_day -= ONE_DAY
#     return possible_previous_day 

# previous_business_day(date(2026, 1, 7), holidays)
# ---------------------------------------------------------------------------
# Tests: don't change these. Run the file to see what passes.
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
