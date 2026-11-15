"""
Problem 3 — A Small Bank Account Class (SOLUTION)

Key idea: CHECK everything first, then CHANGE state. That way a failed
operation never leaves an account half-updated.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


class InsufficientFundsError(Exception):
    """Raised when an account doesn't have enough money for a withdrawal or transfer."""


def to_money(amount):
    """
    Convert a string or Decimal into a Decimal rounded to the cent.
    Raises ValueError for anything that isn't a valid number.
    """
    try:
        # str() first, so Decimal("10.00") and "10.00" both work the same way.
        return Decimal(str(amount)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        raise ValueError(f"Not a valid amount: {amount!r}")


def to_positive_money(amount):
    """Like to_money, but also rejects zero and negative amounts."""
    money = to_money(amount)
    if money <= 0:
        raise ValueError(f"Amount must be positive, got {money}")
    return money


class BankAccount:
    def __init__(self, owner, opening_balance="0.00"):
        opening = to_money(opening_balance)
        if opening < 0:
            raise ValueError("Opening balance can't be negative")

        self.owner = owner
        # The leading underscore says "internal: don't set this from outside."
        # Changes go through deposit / withdraw / transfer_to only.
        self._balance = opening
        self.history = []

    @property
    def balance(self):
        """Read-only view of the balance. account.balance = 5 will raise an error."""
        return self._balance

    def deposit(self, amount):
        money = to_positive_money(amount)
        self._balance += money
        self.history.append(("deposit", money))
        return self._balance

    def withdraw(self, amount):
        money = to_positive_money(amount)

        # Check first...
        if money > self._balance:
            raise InsufficientFundsError(
                f"{self.owner} has {self._balance}, tried to withdraw {money}"
            )

        # ...then change.
        self._balance -= money
        self.history.append(("withdrawal", money))
        return self._balance

    def transfer_to(self, other_account, amount):
        # Run EVERY check before touching either account. If any check fails,
        # we raise before anything has changed, so the transfer is all-or-nothing.
        if other_account is self:
            raise ValueError("Can't transfer to the same account")

        money = to_positive_money(amount)

        if money > self._balance:
            raise InsufficientFundsError(
                f"{self.owner} has {self._balance}, tried to transfer {money}"
            )

        # All checks passed. Now update both sides.
        self._balance -= money
        other_account._balance += money

        self.history.append(("transfer_out", money))
        other_account.history.append(("transfer_in", money))

    def __repr__(self):
        # Makes printing an account readable while debugging.
        return f"BankAccount(owner={self.owner!r}, balance={self._balance})"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    # Basic deposit and withdraw
    acct = BankAccount("Alice", "100.00")
    assert acct.deposit("50.25") == Decimal("150.25")
    assert acct.withdraw("0.25") == Decimal("150.00")
    assert acct.history == [("deposit", Decimal("50.25")), ("withdrawal", Decimal("0.25"))]

    # Overdraft is refused and nothing changes
    try:
        acct.withdraw("1000")
        assert False, "should have raised InsufficientFundsError"
    except InsufficientFundsError:
        pass
    assert acct.balance == Decimal("150.00")

    # Zero, negative, and garbage amounts are refused
    for bad in ["0", "-5", "abc", None]:
        try:
            acct.deposit(bad)
            assert False, f"should have rejected {bad!r}"
        except ValueError:
            pass

    # Negative opening balance is refused
    try:
        BankAccount("Bad", "-1")
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    # A successful transfer updates both accounts and both histories
    alice = BankAccount("Alice", "100.00")
    bob = BankAccount("Bob")
    alice.transfer_to(bob, "30.00")
    assert alice.balance == Decimal("70.00")
    assert bob.balance == Decimal("30.00")
    assert alice.history == [("transfer_out", Decimal("30.00"))]
    assert bob.history == [("transfer_in", Decimal("30.00"))]

    # A failed transfer changes NOTHING on either side
    try:
        alice.transfer_to(bob, "999.00")
        assert False, "should have raised InsufficientFundsError"
    except InsufficientFundsError:
        pass
    assert alice.balance == Decimal("70.00")
    assert bob.balance == Decimal("30.00")
    assert len(alice.history) == 1 and len(bob.history) == 1

    # Transfer to yourself is refused
    try:
        alice.transfer_to(alice, "1.00")
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    # balance can't be set from outside
    try:
        alice.balance = Decimal("1000000")
        assert False, "balance should be read-only"
    except AttributeError:
        pass

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
