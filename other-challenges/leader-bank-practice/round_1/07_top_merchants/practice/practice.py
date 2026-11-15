"""
Problem 7 — Top K Merchants (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from collections import Counter, defaultdict
from decimal import Decimal


def normalize(name):
    """Make " Starbucks " and "starbucks" the same key."""
    # TODO
    raise NotImplementedError


def top_merchants_by_count(transactions, k):
    # TODO: return [] when k <= 0
    # TODO: count visits per normalized name, and remember the first spelling seen
    # TODO: sort by (-count, name) and take the first k
    raise NotImplementedError


def top_merchants_by_spend(transactions, k):
    # TODO: same as above, but add up Decimal(amount) instead of counting
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
# ---------------------------------------------------------------------------
def run_tests():
    transactions = [
        {"merchant": "Starbucks", "amount": "5.75"},
        {"merchant": "Shell", "amount": "40.00"},
        {"merchant": "Starbucks", "amount": "6.10"},
        {"merchant": "Amazon", "amount": "89.99"},
        {"merchant": "Shell", "amount": "38.20"},
        {"merchant": "Starbucks", "amount": "4.95"},
    ]

    assert top_merchants_by_count(transactions, 2) == [("Starbucks", 3), ("Shell", 2)]
    assert top_merchants_by_count(transactions, 10) == [
        ("Starbucks", 3), ("Shell", 2), ("Amazon", 1)
    ]
    assert top_merchants_by_count(transactions, 0) == []
    assert top_merchants_by_count([], 3) == []

    tie = [{"merchant": "Zara", "amount": "1"}, {"merchant": "Apple", "amount": "1"}]
    assert top_merchants_by_count(tie, 2) == [("Apple", 1), ("Zara", 1)]

    messy = [
        {"merchant": "Starbucks", "amount": "1"},
        {"merchant": " starbucks ", "amount": "1"},
        {"merchant": "STARBUCKS", "amount": "1"},
    ]
    assert top_merchants_by_count(messy, 1) == [("Starbucks", 3)]

    assert top_merchants_by_spend(transactions, 2) == [
        ("Amazon", Decimal("89.99")), ("Shell", Decimal("78.20"))
    ]
    assert top_merchants_by_spend(transactions, 3)[2] == ("Starbucks", Decimal("16.80"))
    assert top_merchants_by_spend(transactions, -1) == []

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
