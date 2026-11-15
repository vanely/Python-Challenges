# Problem 3 — A Small Bank Account Class

Build a `BankAccount` class that supports:

| Method | Behavior |
|---|---|
| `BankAccount(owner, opening_balance="0.00")` | Create the account. The opening balance can't be negative. |
| `deposit(amount)` | Add money. Returns the new balance. |
| `withdraw(amount)` | Remove money. Returns the new balance. |
| `transfer_to(other_account, amount)` | Move money from this account to another one. |
| `balance` | The current balance, as a `Decimal`. |
| `history` | A list of every successful action as `(kind, amount)` tuples. |

## Rules

- Amounts can arrive as strings or Decimals. Store everything as `Decimal`, rounded to the cent.
- Zero or negative amounts raise `ValueError`.
- Withdrawing or transferring more than the balance raises a custom `InsufficientFundsError`.
- **A transfer is all-or-nothing.** If it fails, *neither* account changes and nothing goes into either history.
- Transferring to the same account raises `ValueError`.
- History kinds to record:
  - `"deposit"` / `"withdrawal"` for `deposit` / `withdraw`
  - `"transfer_out"` on the sender and `"transfer_in"` on the receiver for a successful `transfer_to`

## Example

```python
alice = BankAccount("Alice", "100.00")
bob = BankAccount("Bob")

alice.transfer_to(bob, "30.00")
alice.balance   # Decimal("70.00")
bob.balance     # Decimal("30.00")
alice.history   # [("transfer_out", Decimal("30.00"))]
bob.history     # [("transfer_in", Decimal("30.00"))]

alice.withdraw("500")   # raises InsufficientFundsError, balance still 70.00
alice.transfer_to(alice, "1.00")  # raises ValueError
```

## Things to talk about

- Why a custom exception instead of returning `False`? The caller can't accidentally ignore it, and it carries a clear meaning.
- In a real bank this lives in a database. An all-or-nothing transfer means a **database transaction**: both updates commit, or neither does.
- With two requests at once, you'd need locking (`SELECT ... FOR UPDATE`) so two withdrawals can't both see the old balance.
