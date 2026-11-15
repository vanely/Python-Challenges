# Round 1 — Practical Python Practice (Leader Bank prep)

Eight short problems, each sized for a 20–30 minute interview round.

## Folder layout

```
round_1/
  01_transaction_summary/
    README.md            <- the problem description (read this first)
    practice/practice.py <- starter code: YOU fill in the functions
    solution/solution.py <- a worked, commented solution
  02_routing_number/
  ...
```

## How to practice

1. Read the problem's `README.md`.
2. Set a timer for 25 minutes.
3. Open `practice/practice.py` and fill in every spot marked `TODO`.
4. Run it. The tests at the bottom tell you what passes:

   ```bash
   python3 round_1/01_transaction_summary/practice/practice.py
   ```

5. Only then open `solution/solution.py` and compare.

Every file runs on its own, with no installs needed (standard library only).

## Habits to show the interviewer (say these out loud)

- **Money uses `Decimal`, never `float`.** `0.1 + 0.2 == 0.30000000000000004` in floats.
  Build Decimals from strings: `Decimal("19.99")`, not `Decimal(19.99)`.
- **Round to the cent explicitly:** `amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.
- **Restate the problem and your assumptions** in the first 2 minutes.
- **Name the edge cases:** empty input, negative or zero amounts, duplicates, rounding.
- **Get it working first, then clean it up.**
- **Finish with a few `assert` tests.**

## The problems

| # | Folder | Skill it practices |
|---|--------|--------------------|
| 1 | `01_transaction_summary` | dicts, `defaultdict`, processing records in order |
| 2 | `02_routing_number` | input validation, string → digits, checksums |
| 3 | `03_bank_account` | classes, custom exceptions, keeping state consistent |
| 4 | `04_mortgage_calculator` | formulas with `Decimal`, rounding, building a schedule |
| 5 | `05_merge_rate_locks` | sorting + merging intervals |
| 6 | `06_suspicious_withdrawals` | sliding window with a `deque` |
| 7 | `07_top_merchants` | `Counter`, sorting with tie-breaks |
| 8 | `08_paginated_api_client` | pagination, retries, exponential backoff, error types |
