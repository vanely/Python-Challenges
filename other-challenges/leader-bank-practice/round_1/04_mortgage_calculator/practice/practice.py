"""
Problem 4 — Mortgage Payment and Amortization Schedule (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def round_cents(value):
    """Round a Decimal to 2 places (0.005 rounds up)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_rate(annual_rate_percent):
    """Turn "6" (percent per year) into 0.005 (decimal per month)."""
    # TODO
    raise NotImplementedError


def monthly_payment(principal, annual_rate_percent, years):
    # TODO: convert inputs to Decimal / ints
    # TODO: raise ValueError for a non-positive principal or term
    # TODO: handle the 0% rate edge case
    # TODO: apply M = P * r * (1 + r)^n / ((1 + r)^n - 1), round to cents
    raise NotImplementedError


def amortization_schedule(principal, annual_rate_percent, years):
    # TODO: loop month by month:
    #   interest = balance * r (rounded)
    #   principal_paid = payment - interest
    #   on the LAST month, pay off exactly the remaining balance
    #   append a dict for the month
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
# ---------------------------------------------------------------------------
def run_tests():
    assert monthly_payment(300000, 6, 30) == Decimal("1798.65")
    assert monthly_payment(12000, 0, 1) == Decimal("1000.00")

    try:
        monthly_payment(0, 6, 30)
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    schedule = amortization_schedule(300000, 6, 30)
    assert len(schedule) == 360

    first = schedule[0]
    assert first["interest"] == Decimal("1500.00")
    assert first["principal"] == Decimal("298.65")
    assert first["balance"] == Decimal("299701.35")

    assert schedule[-1]["balance"] == Decimal("0.00")
    assert sum(row["principal"] for row in schedule) == Decimal("300000.00")
    assert abs(schedule[-1]["payment"] - Decimal("1798.65")) < Decimal("5.00")

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
