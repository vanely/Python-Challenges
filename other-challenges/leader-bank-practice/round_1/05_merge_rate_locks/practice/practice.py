"""
Problem 5 — Merge Overlapping Rate-Lock Periods (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def merge_lock_periods(periods):
    # TODO: raise ValueError if any period ends before it starts
    # TODO: sort a COPY of the periods by start date
    # TODO: walk through them. Extend the last merged period if this one
    #       overlaps or touches it (start <= last_end + ONE_DAY),
    #       otherwise start a new period.
    raise NotImplementedError


def find_unlocked_gaps(periods):
    """Bonus: the stretches between merged periods when there was no lock."""
    # TODO
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
# ---------------------------------------------------------------------------
def run_tests():
    d = date

    periods = [
        (d(2026, 3, 20), d(2026, 4, 5)),
        (d(2026, 3, 1), d(2026, 3, 15)),
        (d(2026, 3, 10), d(2026, 3, 25)),
        (d(2026, 5, 1), d(2026, 5, 30)),
    ]
    original_copy = list(periods)
    assert merge_lock_periods(periods) == [
        (d(2026, 3, 1), d(2026, 4, 5)),
        (d(2026, 5, 1), d(2026, 5, 30)),
    ]
    assert periods == original_copy

    assert merge_lock_periods([]) == []

    assert merge_lock_periods([
        (d(2026, 1, 1), d(2026, 1, 10)),
        (d(2026, 1, 11), d(2026, 1, 20)),
    ]) == [(d(2026, 1, 1), d(2026, 1, 20))]

    assert merge_lock_periods([
        (d(2026, 1, 1), d(2026, 1, 10)),
        (d(2026, 1, 12), d(2026, 1, 20)),
    ]) == [(d(2026, 1, 1), d(2026, 1, 10)), (d(2026, 1, 12), d(2026, 1, 20))]

    assert merge_lock_periods([
        (d(2026, 1, 1), d(2026, 1, 31)),
        (d(2026, 1, 5), d(2026, 1, 6)),
    ]) == [(d(2026, 1, 1), d(2026, 1, 31))]

    try:
        merge_lock_periods([(d(2026, 2, 1), d(2026, 1, 1))])
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    print("Core tests passed!")

    # Bonus
    assert find_unlocked_gaps(periods) == [(d(2026, 4, 6), d(2026, 4, 30))]
    print("Bonus test passed too!")


if __name__ == "__main__":
    run_tests()
