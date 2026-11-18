# Problem 4 — Mortgage Payment and Amortization Schedule

Leader Bank is one of the biggest mortgage lenders in Massachusetts, so this one is very on-brand.

## Part A: `monthly_payment(principal, annual_rate_percent, years)`

Use the standard fixed-rate formula:

```
M = P × r × (1 + r)^n / ((1 + r)^n − 1)

P = principal (loan amount)
r = monthly interest rate = annual rate ÷ 100 ÷ 12
n = number of monthly payments = years × 12
```

Return a `Decimal` rounded to the cent.

**Edge case:** if the rate is `0`, the formula divides by zero. The payment is just `P / n`.

Check: `$300,000` at `6%` for `30` years → **`$1,798.65`**

## Part B: `amortization_schedule(principal, annual_rate_percent, years)`

Return a list with one dict per month:

```python
{"month": 1, "payment": Decimal("1798.65"), "interest": Decimal("1500.00"),
 "principal": Decimal("298.65"), "balance": Decimal("299701.35")}
```

Each month:

1. `interest` = current balance × r, rounded to the cent
2. `principal` = payment − interest
3. `balance` = old balance − principal

Because of rounding, the last month would leave a few cents behind. **Adjust the final payment** so the balance ends at exactly `0.00`.

## Things to talk about

- Interest is front-loaded. In month 1 of the example, $1,500 of the $1,798.65 is interest.
- Why build the schedule from the *rounded* payment? It's the amount the borrower actually pays.
- `Decimal` supports `**` with integer exponents, so `(1 + r) ** n` works fine.
