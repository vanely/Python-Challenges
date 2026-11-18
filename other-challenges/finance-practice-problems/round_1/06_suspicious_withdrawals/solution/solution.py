"""
Problem 6 — Flag Suspicious Withdrawal Activity (SOLUTION)

Sliding window: for each account, keep a deque of timestamps that fall
inside the current 24-hour window.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta


def flag_suspicious_accounts(withdrawals, max_count, window=timedelta(hours=24)):
    # Step 1: group the timestamps by account.
    times_by_account = defaultdict(list)
    for account_id, timestamp in withdrawals:
        times_by_account[account_id].append(timestamp)

    flagged = []

    # Step 2: check each account on its own.
    for account_id, times in times_by_account.items():
        times.sort()  # oldest first

        current_window = deque()

        for timestamp in times:
            # Add the newest withdrawal on the right.
            current_window.append(timestamp)

            # Drop old withdrawals from the left until everything left
            # is less than `window` older than the newest one.
            while timestamp - current_window[0] >= window:
                current_window.popleft()

            # Too many inside one window? Flag it and move to the next account.
            if len(current_window) > max_count:
                flagged.append(account_id)
                break

    return sorted(flagged)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    dt = datetime

    withdrawals = [
        ("A1", dt(2026, 11, 2, 9, 0)),
        ("A1", dt(2026, 11, 2, 13, 0)),
        ("A1", dt(2026, 11, 2, 22, 0)),
        ("A1", dt(2026, 11, 2, 23, 30)),
        ("B2", dt(2026, 11, 1, 9, 0)),
        ("B2", dt(2026, 11, 2, 10, 0)),
        ("B2", dt(2026, 11, 3, 11, 0)),
        ("B2", dt(2026, 11, 4, 12, 0)),
    ]
    assert flag_suspicious_accounts(withdrawals, max_count=3) == ["A1"]

    # Works even when the input is shuffled
    assert flag_suspicious_accounts(list(reversed(withdrawals)), max_count=3) == ["A1"]

    # Empty input
    assert flag_suspicious_accounts([], max_count=3) == []

    # Exactly max_count is fine. Only MORE than max_count gets flagged.
    three = [("C3", dt(2026, 1, 1, h, 0)) for h in (1, 2, 3)]
    assert flag_suspicious_accounts(three, max_count=3) == []
    assert flag_suspicious_accounts(three, max_count=2) == ["C3"]

    # Exactly 24 hours apart is NOT the same window
    edge = [
        ("D4", dt(2026, 1, 1, 9, 0)),
        ("D4", dt(2026, 1, 2, 9, 0)),
    ]
    assert flag_suspicious_accounts(edge, max_count=1) == []

    # One minute less than 24 hours IS the same window
    edge = [
        ("D4", dt(2026, 1, 1, 9, 0)),
        ("D4", dt(2026, 1, 2, 8, 59)),
    ]
    assert flag_suspicious_accounts(edge, max_count=1) == ["D4"]

    # Several flagged accounts come back sorted
    many = [("Z9", dt(2026, 1, 1, 1)), ("Z9", dt(2026, 1, 1, 2)),
            ("M5", dt(2026, 1, 1, 1)), ("M5", dt(2026, 1, 1, 2))]
    assert flag_suspicious_accounts(many, max_count=1) == ["M5", "Z9"]

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
