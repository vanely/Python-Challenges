"""
Problem 6 — Flag Suspicious Withdrawal Activity (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta


def flag_suspicious_accounts(withdrawals, max_count, window=timedelta(hours=24)):
    # TODO: group timestamps by account (defaultdict(list))
    # TODO: for each account, sort its times and slide a deque across them:
    #         - append the new time
    #         - popleft while (newest - oldest) >= window
    #         - if len(deque) > max_count, flag the account
    # TODO: return the flagged account ids, sorted
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
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
    assert flag_suspicious_accounts(list(reversed(withdrawals)), max_count=3) == ["A1"]
    assert flag_suspicious_accounts([], max_count=3) == []

    three = [("C3", dt(2026, 1, 1, h, 0)) for h in (1, 2, 3)]
    assert flag_suspicious_accounts(three, max_count=3) == []
    assert flag_suspicious_accounts(three, max_count=2) == ["C3"]

    edge = [("D4", dt(2026, 1, 1, 9, 0)), ("D4", dt(2026, 1, 2, 9, 0))]
    assert flag_suspicious_accounts(edge, max_count=1) == []

    edge = [("D4", dt(2026, 1, 1, 9, 0)), ("D4", dt(2026, 1, 2, 8, 59))]
    assert flag_suspicious_accounts(edge, max_count=1) == ["D4"]

    many = [("Z9", dt(2026, 1, 1, 1)), ("Z9", dt(2026, 1, 1, 2)),
            ("M5", dt(2026, 1, 1, 1)), ("M5", dt(2026, 1, 1, 2))]
    assert flag_suspicious_accounts(many, max_count=1) == ["M5", "Z9"]

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
