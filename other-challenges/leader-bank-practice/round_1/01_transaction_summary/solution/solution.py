"""
Problem 1 — Transaction Summary (SOLUTION)

Walk through the transactions in order, keep a running balance per account,
skip duplicate ids, and reject anything that is invalid or would overdraw.
"""

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# One cent. We use this to round every amount to 2 decimal places.
CENT = Decimal("0.01")


def parse_amount(raw_amount):
    """
    Turn a string like "120.50" into a Decimal rounded to the cent.
    Returns None if the string isn't a valid number.
    """
    try:
        # Build the Decimal from the STRING so we never pick up float rounding errors.
        return Decimal(raw_amount).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        return None


def summarize_transactions(transactions):
    # defaultdict gives every new account a starting balance of 0.00 automatically.
    balances = defaultdict(lambda: Decimal("0.00"))

    seen_ids = set()      # ids we have already processed
    duplicate_ids = []    # ids we saw a second (or third...) time
    rejected_ids = []     # transactions we refused to apply

    for txn in transactions:
        txn_id = txn["id"]
        account = txn["account"]

        # Make sure the account shows up in the output even if every
        # transaction for it is rejected. Reading a defaultdict key creates it.
        balances[account]

        # 1) Duplicates: process only the first copy of each id.
        if txn_id in seen_ids:
            duplicate_ids.append(txn_id)
            continue
        seen_ids.add(txn_id)

        # 2) The amount must be a valid, positive number.
        amount = parse_amount(txn["amount"])
        if amount is None or amount <= 0:
            rejected_ids.append(txn_id)
            continue

        # 3) Apply the transaction based on its type.
        if txn["type"] == "deposit":
            balances[account] += amount

        elif txn["type"] == "withdrawal":
            # Refuse any withdrawal that would push the balance below zero.
            if balances[account] - amount < 0:
                rejected_ids.append(txn_id)
            else:
                balances[account] -= amount

        else:
            # Unknown type, e.g. "refund". Reject it rather than guess.
            rejected_ids.append(txn_id)

    return {
        "balances": dict(balances),  # convert back to a normal dict for output
        "duplicate_ids": duplicate_ids,
        "rejected_ids": rejected_ids,
    }


# ---------------------------------------------------------------------------
# Tests: run this file directly to check everything works.
# ---------------------------------------------------------------------------
def run_tests():
    # The example from the README
    result = summarize_transactions([
        {"id": "t1", "account": "A100", "type": "deposit", "amount": "500.00"},
        {"id": "t2", "account": "A100", "type": "withdrawal", "amount": "120.50"},
        {"id": "t2", "account": "A100", "type": "withdrawal", "amount": "120.50"},
        {"id": "t3", "account": "B200", "type": "withdrawal", "amount": "10.00"},
    ])
    assert result["balances"] == {"A100": Decimal("379.50"), "B200": Decimal("0.00")}
    assert result["duplicate_ids"] == ["t2"]
    assert result["rejected_ids"] == ["t3"]

    # Empty input
    assert summarize_transactions([]) == {"balances": {}, "duplicate_ids": [], "rejected_ids": []}

    # Floats would get this wrong: 0.10 + 0.20 should be exactly 0.30
    result = summarize_transactions([
        {"id": "a", "account": "X", "type": "deposit", "amount": "0.10"},
        {"id": "b", "account": "X", "type": "deposit", "amount": "0.20"},
    ])
    assert result["balances"]["X"] == Decimal("0.30")

    # Negative amount, zero, garbage text, and unknown type are all rejected
    result = summarize_transactions([
        {"id": "n", "account": "X", "type": "deposit", "amount": "-5.00"},
        {"id": "z", "account": "X", "type": "deposit", "amount": "0"},
        {"id": "g", "account": "X", "type": "deposit", "amount": "abc"},
        {"id": "u", "account": "X", "type": "refund", "amount": "5.00"},
    ])
    assert result["rejected_ids"] == ["n", "z", "g", "u"]
    assert result["balances"]["X"] == Decimal("0.00")

    # Withdrawing the exact balance is allowed (balance lands on 0, not below)
    result = summarize_transactions([
        {"id": "1", "account": "X", "type": "deposit", "amount": "50.00"},
        {"id": "2", "account": "X", "type": "withdrawal", "amount": "50.00"},
    ])
    assert result["balances"]["X"] == Decimal("0.00")
    assert result["rejected_ids"] == []

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
