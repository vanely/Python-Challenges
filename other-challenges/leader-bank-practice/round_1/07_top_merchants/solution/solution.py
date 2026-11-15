"""
Problem 7 — Top K Merchants (SOLUTION)

Count (or total) per merchant, then sort by "biggest first, then A to Z".
"""

from collections import Counter, defaultdict
from decimal import Decimal


def normalize(name):
    """ " Starbucks " and "starbucks" become the same key: "starbucks"."""
    return name.strip().lower()


def top_merchants_by_count(transactions, k):
    if k <= 0:
        return []

    counts = Counter()      # normalized name -> number of visits
    display_name = {}       # normalized name -> the spelling we saw first

    for txn in transactions:
        key = normalize(txn["merchant"])
        counts[key] += 1
        # setdefault only stores a value the FIRST time we see this key.
        display_name.setdefault(key, txn["merchant"].strip())

    # Sort by count, highest first. The minus sign flips the order.
    # Ties are broken alphabetically by the second part of the key.
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))

    return [(display_name[key], count) for key, count in ranked[:k]]


def top_merchants_by_spend(transactions, k):
    if k <= 0:
        return []

    totals = defaultdict(lambda: Decimal("0.00"))  # normalized name -> total spent
    display_name = {}

    for txn in transactions:
        key = normalize(txn["merchant"])
        totals[key] += Decimal(txn["amount"])  # Decimal from a string: exact
        display_name.setdefault(key, txn["merchant"].strip())

    # Same sort trick: biggest total first, then A to Z.
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))

    return [(display_name[key], total) for key, total in ranked[:k]]


# ---------------------------------------------------------------------------
# Tests
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

    # Part A
    assert top_merchants_by_count(transactions, 2) == [("Starbucks", 3), ("Shell", 2)]
    assert top_merchants_by_count(transactions, 10) == [
        ("Starbucks", 3), ("Shell", 2), ("Amazon", 1)
    ]
    assert top_merchants_by_count(transactions, 0) == []
    assert top_merchants_by_count([], 3) == []

    # Ties break alphabetically, not in the order they appeared
    tie = [{"merchant": "Zara", "amount": "1"}, {"merchant": "Apple", "amount": "1"}]
    assert top_merchants_by_count(tie, 2) == [("Apple", 1), ("Zara", 1)]

    # Case and spaces are ignored; the first spelling seen is kept
    messy = [
        {"merchant": "Starbucks", "amount": "1"},
        {"merchant": " starbucks ", "amount": "1"},
        {"merchant": "STARBUCKS", "amount": "1"},
    ]
    assert top_merchants_by_count(messy, 1) == [("Starbucks", 3)]

    # Part B
    assert top_merchants_by_spend(transactions, 2) == [
        ("Amazon", Decimal("89.99")), ("Shell", Decimal("78.20"))
    ]
    assert top_merchants_by_spend(transactions, 3)[2] == ("Starbucks", Decimal("16.80"))
    assert top_merchants_by_spend(transactions, -1) == []

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
