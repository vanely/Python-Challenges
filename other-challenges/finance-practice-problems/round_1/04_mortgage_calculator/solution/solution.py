"""
Problem 4 — Mortgage Payment and Amortization Schedule (SOLUTION)
"""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def round_cents(value):
    """Round a Decimal to 2 places the way people expect (0.005 rounds up)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def monthly_rate(annual_rate_percent):
    """Turn an annual percentage like "6" into a monthly decimal rate (0.005)."""
    return Decimal(str(annual_rate_percent)) / Decimal("100") / Decimal("12")


def monthly_payment(principal, annual_rate_percent, years):
    principal = Decimal(str(principal))
    rate = monthly_rate(annual_rate_percent)
    num_payments = int(years) * 12

    if principal <= 0 or num_payments <= 0:
        raise ValueError("Principal and term must be positive")

    # Edge case: a 0% loan. The formula would divide by zero,
    # so just split the principal evenly across the months.
    if rate == 0:
        return round_cents(principal / num_payments)

    # The standard formula:  M = P * r * (1 + r)^n / ((1 + r)^n - 1)
    growth = (1 + rate) ** num_payments
    payment = principal * rate * growth / (growth - 1)

    return round_cents(payment)


def amortization_schedule(principal, annual_rate_percent, years):
    balance = round_cents(Decimal(str(principal)))
    rate = monthly_rate(annual_rate_percent)
    num_payments = int(years) * 12
    payment = monthly_payment(principal, annual_rate_percent, years)

    schedule = []

    for month in range(1, num_payments + 1):
        # 1) Interest for this month is charged on what's still owed.
        interest = round_cents(balance * rate)

        # 2) Whatever is left of the payment goes toward the loan itself.
        principal_paid = payment - interest

        # 3) Last month: pay off exactly what's left, so rounding
        #    doesn't leave a few cents hanging.
        if month == num_payments:
            principal_paid = balance
            this_payment = interest + principal_paid
        else:
            this_payment = payment

        balance = balance - principal_paid

        schedule.append({
            "month": month,
            "payment": this_payment,
            "interest": interest,
            "principal": principal_paid,
            "balance": balance,
        })

    return schedule


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    # The well-known example: $300k, 6%, 30 years
    assert monthly_payment(300000, 6, 30) == Decimal("1798.65")

    # 0% loan: $12,000 over 1 year is $1,000 a month
    assert monthly_payment(12000, 0, 1) == Decimal("1000.00")

    # Bad input
    try:
        monthly_payment(0, 6, 30)
        assert False, "should have raised ValueError"
    except ValueError:
        pass

    schedule = amortization_schedule(300000, 6, 30)

    # One row per month
    assert len(schedule) == 360

    # Month 1: interest is 300,000 × 0.005 = 1,500.00
    first = schedule[0]
    assert first["interest"] == Decimal("1500.00")
    assert first["principal"] == Decimal("298.65")
    assert first["balance"] == Decimal("299701.35")

    # The loan ends at exactly zero
    assert schedule[-1]["balance"] == Decimal("0.00")

    # All the principal payments add up to the original loan
    total_principal = sum(row["principal"] for row in schedule)
    assert total_principal == Decimal("300000.00")

    # The final payment is close to the regular one (within a few dollars)
    assert abs(schedule[-1]["payment"] - Decimal("1798.65")) < Decimal("5.00")

    print("All tests passed!")
    total_interest = sum(row["interest"] for row in schedule)
    print(f"  Total interest paid over 30 years: ${total_interest:,}")


if __name__ == "__main__":
    run_tests()
