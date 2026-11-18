"""
Problem 3 — A Small Bank Account Class (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


class InsufficientFundsError(Exception):
    """Raised when an account doesn't have enough money."""


def to_money(amount):
    """Convert a string/Decimal to a Decimal rounded to the cent. Raise ValueError if invalid."""
    # TODO (hint: Decimal(str(amount)).quantize(CENT, rounding=ROUND_HALF_UP), and catch InvalidOperation and TypeError)
    raise NotImplementedError


def to_positive_money(amount):
    """Like to_money, but also raise ValueError for zero or negative amounts."""
    # TODO
    raise NotImplementedError


class BankAccount:
    def __init__(self, owner, opening_balance="0.00"):
        # TODO: validate the opening balance (no negatives)
        # TODO: store owner, _balance, and an empty history list
        raise NotImplementedError

    @property
    def balance(self):
        # TODO: return the balance (a property makes it read-only from outside)
        raise NotImplementedError

    def deposit(self, amount):
        # TODO: validate, add, record in history, return the new balance
        raise NotImplementedError

    def withdraw(self, amount):
        # TODO: validate, CHECK funds first, then subtract, record, return the new balance
        raise NotImplementedError

    def transfer_to(self, other_account, amount):
        # TODO: run ALL checks before changing either account (all-or-nothing)
        # TODO: then update both balances and both histories
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
# ---------------------------------------------------------------------------
def run_tests():
    acct = BankAccount("Alice", "100.00")
    assert acct.deposit("50.25") == Decimal("150.25")
    assert acct.withdraw("0.25") == Decimal("150.00")
    assert acct.history == [("deposit", Decimal("50.25")), ("withdrawal", Decimal("0.25"))]

    try:
        acct.withdraw("1000")
        assert False, "should have raised InsufficientFundsError"
    except InsufficientFundsError:
        pass
    assert acct.balance == Decimal("150.00")

    for bad in ["0", "-5", "abc", None]:
        try:
            acct.deposit(bad)
            assert False, f"should have rejected {bad!r}"
        except ValueError:
            pass

    try:
        BankAccount("Bad", "-1")
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    alice = BankAccount("Alice", "100.00")
    bob = BankAccount("Bob")
    alice.transfer_to(bob, "30.00")
    assert alice.balance == Decimal("70.00")
    assert bob.balance == Decimal("30.00")
    assert alice.history == [("transfer_out", Decimal("30.00"))]
    assert bob.history == [("transfer_in", Decimal("30.00"))]

    try:
        alice.transfer_to(bob, "999.00")
        assert False, "should have raised InsufficientFundsError"
    except InsufficientFundsError:
        pass
    assert alice.balance == Decimal("70.00")
    assert bob.balance == Decimal("30.00")
    assert len(alice.history) == 1 and len(bob.history) == 1

    try:
        alice.transfer_to(alice, "1.00")
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    try:
        alice.balance = Decimal("1000000")
        assert False, "balance should be read-only"
    except AttributeError:
        pass

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
