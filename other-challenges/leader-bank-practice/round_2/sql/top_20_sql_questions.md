# Top 20 SQL Interview Questions — Explained in Depth

Each question has:
- **Say this first:** your opening line
- **The explanation**
- **A query**
- **💡 The detail most people don't know**

**Every query here is real and tested.** `sql_examples.py` builds this exact database in SQLite and checks each result. Where Postgres syntax differs (Leader Bank lists PostgreSQL and MySQL), the Postgres version is shown too.

### The practice database

```
customers    (customer_id, name, state)               -- Dev has no accounts; Eli's state is NULL
accounts     (account_id, customer_id, type)          -- Eli's account 501 has no transactions
transactions (txn_id, account_id, txn_date, amount_cents)   -- + deposit, - withdrawal
loans        (loan_id, customer_id, officer, amount, status)
```

> The demo stores money as **integer cents** because SQLite has no exact decimal type. In Postgres, money columns should be `NUMERIC(12, 2)`, never `FLOAT` (see question 18).

---

## 1. In what order does SQL actually run a query?

**Say this first:** Not the order it's written. Logically it's: **FROM / JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT**.

**Why it matters:** this one fact explains many confusing errors:
- **You can't use a `SELECT` alias in `WHERE`** (in Postgres and standard SQL). `WHERE` runs *before* `SELECT` has created the alias. `ORDER BY` runs after `SELECT`, so aliases work there.
- **You can't use aggregates like `SUM()` in `WHERE`.** The groups don't exist yet, which is exactly why `HAVING` exists (question 4).
- **Window functions** (question 7) are calculated during the `SELECT` step, so you can't filter on them in `WHERE` either. Wrap the query in a CTE and filter outside (see question 8).

💡 This is the *logical* order. The database's optimizer may physically do things in a different order, for example applying a filter early, as long as the result is the same.

---

## 2. Explain the types of JOIN.

**Say this first:**
- **INNER JOIN** keeps only rows that match on both sides.
- **LEFT JOIN** keeps *every* row from the left table, with NULLs where there's no match.
- **RIGHT JOIN** is the mirror of LEFT.
- **FULL OUTER JOIN** keeps everything from both sides.
- **CROSS JOIN** pairs every row with every row.

```sql
-- INNER: only customers WITH accounts (Dev disappears)
SELECT c.name, a.account_id
FROM customers c
JOIN accounts a ON a.customer_id = c.customer_id;

-- LEFT: every customer, account_id is NULL for Dev
SELECT c.name, a.account_id
FROM customers c
LEFT JOIN accounts a ON a.customer_id = c.customer_id;
```

**Also know:**
- A **self join** joins a table to itself, e.g. employees to their managers, or matching a transfer's outgoing and incoming sides.
- Joins on several columns are common in banking: `ON t.account_id = a.account_id AND t.txn_date = a.as_of_date`.

💡 **A `WHERE` condition on the *right-hand* table quietly turns a LEFT JOIN into an INNER JOIN.**
- In `LEFT JOIN accounts a ON ... WHERE a.type = 'checking'`, customers with no account have `a.type = NULL`, which fails the `WHERE`, so they vanish.
- To keep them, put the condition in the `ON` clause: `LEFT JOIN accounts a ON a.customer_id = c.customer_id AND a.type = 'checking'`.

---

## 3. Find customers who have no transactions.

**Say this first:** This is an **anti-join**: rows in A with no match in B. I'd use `NOT EXISTS`. It's clear, it handles NULLs correctly, and databases optimize it well. A `LEFT JOIN ... IS NULL` also works.

```sql
SELECT c.name
FROM customers c
WHERE NOT EXISTS (
    SELECT 1
    FROM accounts a
    JOIN transactions t ON t.account_id = a.account_id
    WHERE a.customer_id = c.customer_id
);
-- Dev (no accounts) and Eli (account, but no transactions)
```

The `LEFT JOIN` version needs care here, because a customer can have several accounts:

```sql
SELECT c.name
FROM customers c
LEFT JOIN accounts a     ON a.customer_id = c.customer_id
LEFT JOIN transactions t ON t.account_id  = a.account_id
GROUP BY c.customer_id, c.name
HAVING COUNT(t.txn_id) = 0;
```

A plain `WHERE t.txn_id IS NULL` without the `GROUP BY` would wrongly include a customer who has one *active* account and one *empty* account.

💡 **The `NOT IN` + NULL trap:** `WHERE customer_id NOT IN (SELECT customer_id FROM blocked)` returns **zero rows** if the subquery contains even one NULL.
- `x NOT IN (1, NULL)` means `x <> 1 AND x <> NULL`.
- Anything compared to NULL is "unknown," never true.
- `NOT EXISTS` doesn't have this problem. The test script shows both.

---

## 4. What's the difference between WHERE and HAVING?

**Say this first:** `WHERE` filters **rows before grouping**; `HAVING` filters **groups after grouping**. So `HAVING` can use aggregates like `SUM()` and `COUNT()`.

```sql
-- Accounts with at least $1,000 in deposits
SELECT account_id, SUM(amount_cents) AS deposits_cents
FROM transactions
WHERE amount_cents > 0                 -- row filter: deposits only
GROUP BY account_id
HAVING SUM(amount_cents) >= 100000;    -- group filter: $1,000+
```

**Conditional aggregation:** computing several totals in one pass with `CASE`. Interviewers love this:

```sql
SELECT account_id,
       SUM(CASE WHEN amount_cents > 0 THEN  amount_cents ELSE 0 END) AS deposits,
       SUM(CASE WHEN amount_cents < 0 THEN -amount_cents ELSE 0 END) AS withdrawals
FROM transactions
GROUP BY account_id;
```

💡 Filter in `WHERE` whenever you can. Throwing rows away *before* grouping means less work. Use `HAVING` only for conditions that need the aggregate. Postgres also offers the neat shortcut `SUM(amount) FILTER (WHERE amount > 0)`.

---

## 5. COUNT(*) vs COUNT(column) vs COUNT(DISTINCT column)?

**Say this first:**
- `COUNT(*)` counts **rows**.
- `COUNT(col)` counts rows where `col` is **not NULL**.
- `COUNT(DISTINCT col)` counts **unique non-NULL values**.

```sql
SELECT COUNT(*), COUNT(state), COUNT(DISTINCT state) FROM customers;
-- 5, 4, 2     (Eli's state is NULL; the states are MA and NH)
```

**Also:** every aggregate except `COUNT(*)` **ignores NULLs**. So `AVG(col)` is the average of the non-NULL values, which may not be what the business means. Sometimes you want `AVG(COALESCE(col, 0))`.

💡 **With a LEFT JOIN, `COUNT(*)` counts the empty "no match" row as 1.** A customer with no transactions would show 1, not 0. Count a column from the right-hand table (`COUNT(t.txn_id)`) to get the true 0. That's exactly what question 3's `HAVING` relies on.

---

## 6. How does NULL behave?

**Say this first:** NULL means **"unknown,"** not zero or empty. Any comparison with NULL gives *unknown*, not true or false. So `= NULL` never matches anything; you must use `IS NULL` / `IS NOT NULL`.

```sql
SELECT name FROM customers WHERE state = NULL;    -- 0 rows (always!)
SELECT name FROM customers WHERE state IS NULL;   -- Eli
SELECT COALESCE(state, 'Unknown') FROM customers; -- first non-NULL value
```

**Deeper:** SQL uses **three-valued logic**: true, false, unknown. `WHERE` keeps only *true* rows. `NULL + 5` is NULL. `NULLIF(a, b)` returns NULL when `a = b`, which is handy for avoiding divide-by-zero: `x / NULLIF(y, 0)`.

💡 **`WHERE state <> 'MA'` does *not* return Eli**, because "is unknown different from MA?" is unknown. To include NULLs, use `state <> 'MA' OR state IS NULL`, or in Postgres, `state IS DISTINCT FROM 'MA'`, which treats NULL as a normal comparable value.

---

## 7. Calculate a running balance (window functions).

**Say this first:** I'd use a **window function**: `SUM(...) OVER (PARTITION BY account ORDER BY date)`. Unlike `GROUP BY`, window functions **keep every row** and add a calculated column that looks at related rows.

```sql
SELECT account_id, txn_date, amount_cents,
       SUM(amount_cents) OVER (
           PARTITION BY account_id                 -- restart for each account
           ORDER BY txn_date, txn_id               -- in time order (txn_id breaks ties)
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_balance
FROM transactions;
-- account 101: 1000.00 -> 800.00 -> 750.00 -> 875.50
```

**The parts:**
- `PARTITION BY` is like GROUP BY, but rows aren't collapsed.
- `ORDER BY` sets the order inside each partition.
- The **frame** (`ROWS BETWEEN ...`) says which rows to include.

**Also useful:**
- A 7-day moving average: `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`
- Percent of total: `amount * 100.0 / SUM(amount) OVER (PARTITION BY account_id)`

💡 **The default frame isn't what most people assume.** When you add `ORDER BY` without a frame, the default is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. `RANGE` treats rows with the **same `ORDER BY` value as one group**, so two transactions on the same date both show the *combined* total. The test script shows it: the default gives `600, 600`, and `ROWS` gives `300, 600`. For running balances, **always write `ROWS` and add a tie-breaker** like `txn_id`.

---

## 8. ROW_NUMBER vs RANK vs DENSE_RANK, and "top N per group."

**Say this first:** All three number rows in order. They differ only on **ties**:
- `ROW_NUMBER`: 1, 2, 3, 4, always unique, ties broken arbitrarily unless you add a tie-breaker.
- `RANK`: 1, 1, 3, 4. Ties share a rank, then it **skips**.
- `DENSE_RANK`: 1, 1, 2, 3. Ties share a rank, **no gaps**.

```
loan  amount   ROW_NUMBER  RANK  DENSE_RANK
L3    600000   1           1     1
L5    600000   2           1     1
L1    450000   3           3     2
L2    300000   4           4     3
```

**Top loan per officer**, the classic "top N per group" pattern:
```sql
WITH ranked AS (
    SELECT officer, loan_id, amount,
           ROW_NUMBER() OVER (PARTITION BY officer ORDER BY amount DESC, loan_id) AS rn
    FROM loans
)
SELECT officer, loan_id, amount FROM ranked WHERE rn = 1;
```
This is also the standard way to get **"the latest row per account"**: `ORDER BY updated_at DESC`, then `rn = 1`.

💡 You must wrap it in a CTE or subquery, because you can't filter on a window function in `WHERE` (question 1). Postgres also has the shortcut `SELECT DISTINCT ON (officer) ... ORDER BY officer, amount DESC`.

---

## 9. Find the second-highest (or Nth-highest) value.

**Say this first:** For second-highest: `MAX` of everything below the `MAX`. For any N, use `DENSE_RANK`, so ties don't throw off the count.

```sql
SELECT MAX(amount) FROM loans
WHERE amount < (SELECT MAX(amount) FROM loans);         -- 450000

SELECT DISTINCT amount FROM (
    SELECT amount, DENSE_RANK() OVER (ORDER BY amount DESC) AS dr FROM loans
) ranked WHERE dr = 2;                                   -- 450000
```

💡 **`ORDER BY amount DESC LIMIT 1 OFFSET 1` is the common wrong answer.** There are two loans at $600,000, so it returns $600,000 again. Always ask the interviewer: *"Second-highest distinct value, or second row?"* Asking shows care.

---

## 10. LAG and LEAD

**Say this first:** `LAG(col)` gets the value from the **previous** row (in the window's order); `LEAD(col)` gets the **next** one. They're perfect for "change since last time" questions.

```sql
SELECT txn_id, txn_date,
       LAG(txn_date) OVER (PARTITION BY account_id ORDER BY txn_date, txn_id) AS prev_date
FROM transactions;
-- Postgres (with a DATE column): txn_date - LAG(txn_date) OVER (...) gives the days between
```

**Banking uses:**
- Days between transactions (dormant-account detection)
- Balance change month over month
- Detecting when a loan's **status changed** (`WHERE status <> LAG(status) OVER (...)`)
- Spotting rapid repeated withdrawals: the SQL version of Round 1, problem 6

💡 `LAG(col, 2, 0)`: the second argument looks 2 rows back, and the third is the **default** used instead of NULL on the first rows.

---

## 11. What is a CTE? What about a recursive CTE?

**Say this first:** A CTE (`WITH name AS (...)`) is a **named temporary result** you can use in the rest of the query. It's mostly for **readability**: breaking a big query into named steps. A **recursive CTE** refers to itself, which handles hierarchies (an org chart, parent and child accounts) or generating sequences like dates.

```sql
-- Days in Nov 1-7 with no transactions at all
WITH RECURSIVE days(d) AS (
    SELECT '2026-11-01'                                   -- starting row
    UNION ALL
    SELECT date(d, '+1 day') FROM days WHERE d < '2026-11-07'   -- repeat until done
)
SELECT d FROM days
WHERE d NOT IN (SELECT txn_date FROM transactions);       -- 2026-11-06
-- Postgres shortcut: generate_series('2026-11-01'::date, '2026-11-07', '1 day')
```

💡 **In Postgres before version 12, a CTE was always computed separately** (an "optimization fence"), which could make it slower than a subquery. Since version 12, Postgres folds simple CTEs into the main query automatically. You can still force either behavior with `AS MATERIALIZED` / `AS NOT MATERIALIZED`.

---

## 12. Subquery vs. JOIN? What's a correlated subquery?

**Say this first:** A **subquery** is a query inside another query. A **correlated** subquery refers to the outer row, so it's conceptually re-run for each row. Many subqueries can be rewritten as joins, and modern optimizers often do that for you. I pick whichever is clearest, then check the plan if it's slow.

```sql
-- Transactions bigger than THEIR OWN account's average (correlated)
SELECT t.txn_id, t.account_id, t.amount_cents
FROM transactions t
WHERE t.amount_cents > (
    SELECT AVG(t2.amount_cents) FROM transactions t2
    WHERE t2.account_id = t.account_id         -- refers to the outer row
);
```

The same thing with a window function, often faster because it makes one pass:
```sql
SELECT * FROM (
    SELECT t.*, AVG(amount_cents) OVER (PARTITION BY account_id) AS acct_avg
    FROM transactions t
) x WHERE amount_cents > acct_avg;
```

💡 **`EXISTS` stops at the first match**, so for "does any related row exist?" it's often faster than `COUNT(*) > 0`, which has to count every match.

---

## 13. Find and remove duplicate rows.

**Say this first:** Find them with `GROUP BY` on the columns that define "duplicate," plus `HAVING COUNT(*) > 1`. Remove them by keeping one row per group, usually the lowest ID, and deleting the rest.

```sql
-- Find
SELECT account_id, txn_date, amount_cents, COUNT(*) AS copies
FROM transactions
GROUP BY account_id, txn_date, amount_cents
HAVING COUNT(*) > 1;

-- Delete, keeping the lowest txn_id in each group
DELETE FROM transactions
WHERE txn_id NOT IN (
    SELECT MIN(txn_id) FROM transactions
    GROUP BY account_id, txn_date, amount_cents
);
```

In Postgres, `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY txn_id)` with `WHERE rn > 1` is the other common pattern.

**Talk about the business side:** two $300 deposits on the same day **might both be real**. Before deleting, I'd confirm with the business what counts as a true duplicate (same vendor reference ID?). Then I'd fix the cause with a `UNIQUE` constraint or idempotency key (question 20, Design 1), so it can't happen again.

💡 Run destructive statements inside a transaction (`BEGIN; DELETE ...; SELECT ...` to check, then `COMMIT` or `ROLLBACK`). On real bank data, take a backup or copy the rows to an audit table first.

---

## 14. What is an index, and when does it help or hurt?

**Say this first:** An index is a separate, sorted structure (usually a **B-tree**) that lets the database **jump to matching rows instead of scanning the whole table**, like the index at the back of a book. It speeds up reads, but every `INSERT`, `UPDATE`, and `DELETE` must also update every index, so indexes **slow down writes** and use disk space.

```sql
CREATE INDEX idx_txn_account_date ON transactions (account_id, txn_date);
```

**The leftmost-prefix rule for multi-column ("composite") indexes:**
- This index helps `WHERE account_id = ?` and `WHERE account_id = ? AND txn_date >= ?`.
- It does **not** help `WHERE txn_date >= ?` alone, just as a phone book sorted by last name can't find everyone named "Sam."
- The test script shows the plan switch from `SEARCH ... USING INDEX` to a full `SCAN`.

**When an index usually *isn't* used:**
- A function on the column: `WHERE LOWER(email) = ...`. The fix is an *expression index* on `LOWER(email)`.
- A leading wildcard: `LIKE '%smith'`
- Very small tables, or filters that match most of the table (the scan is cheaper)

**Covering index:** if the index contains every column the query needs, the database never touches the table itself. In Postgres this is an "index-only scan"; `INCLUDE (col)` adds extra columns to an index.

💡 **Postgres does NOT automatically index foreign key columns** (MySQL's InnoDB does). Joins on `accounts.customer_id`, and deletes from `customers`, can be slow until you add that index yourself. That's a classic real-world performance bug.

---

## 15. How do you find out why a query is slow? (Plus the N+1 problem)

**Say this first:** Run **`EXPLAIN`** to see the database's plan, and **`EXPLAIN ANALYZE`** (Postgres) to actually run it and see real timings and row counts. I look for full table scans on big tables, row-count estimates far off from the actual numbers, and expensive sorts. Then I fix it with indexes, query rewrites, or updated table statistics (`ANALYZE`).

**What to look for in a Postgres plan:**
- `Seq Scan` on a big table: missing index?
- `Index Scan` / `Index Only Scan`: good
- `Nested Loop` over many rows: maybe a missing index on the join column
- Estimated rows = 10 but actual rows = 1,000,000: stale statistics, so run `ANALYZE`

**The N+1 query problem** (important since you've used Django): loading 100 loans and then accessing `loan.customer.name` in a loop runs **1 query for the loans + 100 queries for the customers**.
- **Fix in Django:**
  - `Loan.objects.select_related("customer")` adds a SQL **JOIN**, for foreign keys and one-to-one relations.
  - `prefetch_related("payments")` runs **one extra query** for many-related items and joins them up in Python.
- **How to spot it:** query counts in the logs, Django Debug Toolbar, or `assertNumQueries` in tests.

💡 **`EXPLAIN ANALYZE` really executes the statement.** Running it on an `UPDATE` or `DELETE` will change data. Wrap it: `BEGIN; EXPLAIN ANALYZE DELETE ...; ROLLBACK;`

---

## 16. What are transactions, ACID, and isolation levels?

**Say this first:** A transaction groups statements so they **all succeed or all fail together**. A transfer debits one account and credits another, and you never want only half. **ACID** stands for:
- **A**tomic: all or nothing
- **C**onsistent: rules and constraints always hold
- **I**solated: concurrent transactions don't step on each other
- **D**urable: once committed, it survives a crash

```sql
BEGIN;
  UPDATE accounts SET balance = balance - 100 WHERE account_id = 101;
  UPDATE accounts SET balance = balance + 100 WHERE account_id = 201;
COMMIT;   -- or ROLLBACK if anything failed
```
The test script shows a failed second insert undoing the first.

**Isolation levels** (from weakest to strongest):

| Level | Prevents |
|---|---|
| Read Uncommitted | (almost nothing): you could see other transactions' uncommitted changes |
| **Read Committed** (Postgres default) | Dirty reads: you only see committed data |
| Repeatable Read (MySQL InnoDB default) | Re-reading a row mid-transaction gives the same answer |
| Serializable | Results are as if transactions ran one at a time; the database may abort one, and you retry |

**The classic banking race, the "lost update":** two withdrawals both read balance = $100, both check "is $100 ≥ $80?", and both subtract. Fixes:
- **Pessimistic locking:** `SELECT balance FROM accounts WHERE account_id = 101 FOR UPDATE;` locks that row until commit, so the second withdrawal waits.
- **Atomic update with a guard:** `UPDATE accounts SET balance = balance - 80 WHERE account_id = 101 AND balance >= 80;` then check that 1 row was updated.
- **Optimistic locking:** add a `version` column, `UPDATE ... WHERE version = 7`. If 0 rows were updated, someone else changed it first, so reload and retry.

💡 **Deadlocks:** if transfer A locks account 1 then 2, while transfer B locks 2 then 1, they wait on each other forever, and the database kills one. The standard fix is to **always lock rows in a consistent order**, e.g. lower account ID first.
💡 Postgres never shows dirty reads, even if you ask for Read Uncommitted. It quietly treats it as Read Committed.

---

## 17. What is normalization, and when would you denormalize?

**Say this first:** Normalization means organizing tables so **each fact is stored once**: customer details in `customers`, not copied onto every transaction. That prevents the copies from going out of sync. I **denormalize** (store copies or pre-computed totals) on purpose for **reporting speed**, accepting the work of keeping the copies up to date.

**The normal forms in plain words:**
- **1NF:** one value per cell, no lists stuffed into a column.
- **2NF / 3NF:** every column describes *the whole key, and nothing but the key*. A customer's address doesn't belong in the loans table.

**OLTP vs OLAP** (ties back to the Snowflake discussion):
- **OLTP** (online transaction processing): the operational database, like Postgres for loans and accounts. Normalized, many small fast reads and writes.
- **OLAP** (analytics): a warehouse like Snowflake. Often a **star schema**: a big **fact** table (transactions) surrounded by **dimension** tables (customer, date, branch). Denormalized for fast large scans and reports.

💡 A daily **balance snapshot** table is a deliberate, very common denormalization in banking. Computing a balance from *every transaction since 2002* every time would be far too slow, so the bank stores end-of-day balances.

---

## 18. What constraints would you use? How should money be stored?

**Say this first:** Constraints let the **database itself** refuse bad data, no matter which app or person writes to it:
- `PRIMARY KEY`
- `FOREIGN KEY` (no transactions for accounts that don't exist)
- `UNIQUE` (no duplicate vendor reference IDs)
- `NOT NULL`
- `CHECK` (loan amount > 0, status in an allowed list)

```sql
CREATE TABLE loans (
    loan_id     TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    amount      NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    status      TEXT NOT NULL CHECK (status IN ('Started', 'Approved', 'Funded', 'Denied'))
);
```

**Money:**
- Use `NUMERIC(12, 2)` (also called `DECIMAL`): exact.
- Or store **integer cents**: also exact, and fast.
- **Never `FLOAT` / `REAL` / `DOUBLE`.** That's the same binary-fraction problem as Python floats (Python question 19).

💡 **Postgres's built-in `money` type is generally discouraged.** Its formatting depends on the server's locale settings, and it handles only one currency.
💡 **A `UNIQUE` column allows multiple NULLs in Postgres by default**, because NULLs are "unknown," so they're not equal to each other. Postgres 15+ can change this with `UNIQUE NULLS NOT DISTINCT`.

---

## 19. UNION vs UNION ALL (plus INTERSECT and EXCEPT)?

**Say this first:** Both stack the results of two queries. `UNION` **removes duplicate rows**, which needs an extra sort or hash step. `UNION ALL` **keeps everything** and is faster. I default to `UNION ALL` unless I truly need duplicates removed.

```sql
SELECT officer FROM loans WHERE status = 'Approved'
UNION                                              -- Kim, Lee
SELECT officer FROM loans WHERE status = 'Funded';
-- with UNION ALL: 4 rows (Kim, Lee, Kim, Kim)
```

**Also:**
- `INTERSECT` gives rows in both results.
- `EXCEPT` (`MINUS` in Oracle) gives rows in the first result but not the second.
- The queries must have the same number of columns, with compatible types.

💡 `EXCEPT` is a quick **data reconciliation** tool: "IDs in the vendor file that aren't in our table," and then the reverse. That's everyday work on integration teams.

---

## 20. How do you paginate large results? And what's an upsert?

**Say this first:** `LIMIT/OFFSET` is simple but gets **slower the deeper you go** and can skip or repeat rows if data changes between pages. For large or live tables I use **keyset pagination**: "give me the next 50 rows *after the last ID I saw*."

```sql
-- OFFSET: page 2,001 makes the database read and throw away 100,000 rows
SELECT * FROM transactions ORDER BY txn_id LIMIT 50 OFFSET 100000;

-- Keyset: jumps straight there using the index
SELECT * FROM transactions WHERE txn_id > :last_seen_id ORDER BY txn_id LIMIT 50;
```

Keyset needs a **unique** sort order. If you sort by date, add the ID as a tie-breaker: `WHERE (txn_date, txn_id) > (:last_date, :last_id)`, a row comparison Postgres supports directly.

**Upsert** ("insert, or update if it already exists"):
```sql
-- Idempotency: record an event once; a retry quietly does nothing
INSERT INTO processed_events (event_id) VALUES ('evt-1')
ON CONFLICT (event_id) DO NOTHING;

-- Sync from a vendor: insert new loans, update existing ones
INSERT INTO loans (loan_id, customer_id, amount, status)
VALUES ('L1', 1, 450000, 'Funded')
ON CONFLICT (loan_id) DO UPDATE SET status = EXCLUDED.status;   -- EXCLUDED = the row we tried to insert
```
MySQL's version is `INSERT ... ON DUPLICATE KEY UPDATE`.

💡 **Check the affected row count after `ON CONFLICT DO NOTHING`:** 1 means "new, go process it," 0 means "already done, skip." That single check is the heart of the idempotent integration worker in Design 1. The test script proves it: the first insert reports 1 row, the retry reports 0.
