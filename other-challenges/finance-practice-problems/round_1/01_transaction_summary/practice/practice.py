"""
Problem 1 — Transaction Summary (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run this file:
    python3 practice.py
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


def parse_amount(raw_amount):
    """
    Turn a string like "120.50" into a Decimal rounded to the cent.
    Return None if the string isn't a valid number.
    Hint: Decimal(raw_amount).quantize(CENT, rounding=ROUND_HALF_UP), and catch InvalidOperation.
    """
    # TODO
    try:
        return Decimal(raw_amount)#.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        return None

# parsed_val = parse_amount("120.49")
# if parsed_val:
#     print(parsed_val)
# else:
    # print("invalid entry")

def summarize_transactions(transactions):
    """
    Return {"balances": {...}, "duplicate_ids": [...], "rejected_ids": [...]}.
    """
    balances = defaultdict(lambda: Decimal("0.00"))

    set_ids = set()
    duplicate_ids = []
    rejected_ids = []

    for txn in transactions:
        txn_id = txn["id"]
        account = txn["account"]

        balances[account]
    # TODO: keep a running balance per account (defaultdict is handy here)
    # TODO: track ids you've already seen so you can spot duplicates
    # TODO: reject invalid amounts, unknown types, and overdrafts
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these. Run the file to see what passes.
# ---------------------------------------------------------------------------
def run_tests():
    result = summarize_transactions([
        {"id": "t1", "account": "A100", "type": "deposit", "amount": "500.00"},
        {"id": "t2", "account": "A100", "type": "withdrawal", "amount": "120.50"},
        {"id": "t2", "account": "A100", "type": "withdrawal", "amount": "120.50"},
        {"id": "t3", "account": "B200", "type": "withdrawal", "amount": "10.00"},
    ])
    assert result["balances"] == {"A100": Decimal("379.50"), "B200": Decimal("0.00")}
    assert result["duplicate_ids"] == ["t2"]
    assert result["rejected_ids"] == ["t3"]

    assert summarize_transactions([]) == {"balances": {}, "duplicate_ids": [], "rejected_ids": []}

    result = summarize_transactions([
        {"id": "a", "account": "X", "type": "deposit", "amount": "0.10"},
        {"id": "b", "account": "X", "type": "deposit", "amount": "0.20"},
    ])
    assert result["balances"]["X"] == Decimal("0.30")

    result = summarize_transactions([
        {"id": "n", "account": "X", "type": "deposit", "amount": "-5.00"},
        {"id": "z", "account": "X", "type": "deposit", "amount": "0"},
        {"id": "g", "account": "X", "type": "deposit", "amount": "abc"},
        {"id": "u", "account": "X", "type": "refund", "amount": "5.00"},
    ])
    assert result["rejected_ids"] == ["n", "z", "g", "u"]
    assert result["balances"]["X"] == Decimal("0.00")

    result = summarize_transactions([
        {"id": "1", "account": "X", "type": "deposit", "amount": "50.00"},
        {"id": "2", "account": "X", "type": "withdrawal", "amount": "50.00"},
    ])
    assert result["balances"]["X"] == Decimal("0.00")
    assert result["rejected_ids"] == []

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
