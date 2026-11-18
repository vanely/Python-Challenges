"""
Problem 5 — Merge Overlapping Rate-Lock Periods (SOLUTION)

The classic "merge intervals" pattern:
  1. Sort by start date.
  2. Walk through the periods. Either extend the last merged one or start a new one.
"""

from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def merge_lock_periods(periods):
    # Validate first so bad data doesn't sneak into the result.
    for start, end in periods:
        if end < start:
            raise ValueError(f"Lock period ends before it starts: {start} -> {end}")

    # sorted() returns a NEW list, so the caller's list is left untouched.
    # Tuples sort by their first item, which is the start date.
    ordered = sorted(periods)

    merged = []
    for start, end in ordered:
        # Nothing merged yet, or there's a real gap of at least one day:
        # start a new period.
        if not merged or start > merged[-1][1] + ONE_DAY:
            merged.append((start, end))
        else:
            # It overlaps or touches the last period, so stretch that one.
            # Use max() because this period may sit entirely inside the last one.
            last_start, last_end = merged[-1]
            merged[-1] = (last_start, max(last_end, end))

    return merged


def find_unlocked_gaps(periods):
    """
    Follow-up: return the (start, end) stretches between lock periods
    when the loan had no lock at all.
    """
    merged = merge_lock_periods(periods)
    gaps = []

    # Look at each pair of neighboring merged periods.
    for (_, previous_end), (next_start, _) in zip(merged, merged[1:]):
        gaps.append((previous_end + ONE_DAY, next_start - ONE_DAY))

    return gaps


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    d = date

    # README example: three overlapping periods collapse into one
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
    assert periods == original_copy  # the caller's list wasn't changed

    # Empty input
    assert merge_lock_periods([]) == []

    # Touching periods (10th, then 11th) merge
    assert merge_lock_periods([
        (d(2026, 1, 1), d(2026, 1, 10)),
        (d(2026, 1, 11), d(2026, 1, 20)),
    ]) == [(d(2026, 1, 1), d(2026, 1, 20))]

    # A one-day gap (10th, then 12th) does NOT merge
    assert merge_lock_periods([
        (d(2026, 1, 1), d(2026, 1, 10)),
        (d(2026, 1, 12), d(2026, 1, 20)),
    ]) == [(d(2026, 1, 1), d(2026, 1, 10)), (d(2026, 1, 12), d(2026, 1, 20))]

    # A period fully inside another doesn't shrink it
    assert merge_lock_periods([
        (d(2026, 1, 1), d(2026, 1, 31)),
        (d(2026, 1, 5), d(2026, 1, 6)),
    ]) == [(d(2026, 1, 1), d(2026, 1, 31))]

    # Invalid period
    try:
        merge_lock_periods([(d(2026, 2, 1), d(2026, 1, 1))])
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    # Follow-up: the gap between the two README periods is Apr 6 to Apr 30
    assert find_unlocked_gaps(periods) == [(d(2026, 4, 6), d(2026, 4, 30))]

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
