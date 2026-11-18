"""
Runs every query in top_20_sql_questions.md against a small in-memory
SQLite database, checks the results, and prints them.

    python3 sql_examples.py

SQLite ships with Python, so there's nothing to install. Where Postgres
syntax differs, the guide shows the Postgres version.

NOTE: SQLite has no exact decimal type, so this demo stores money as
INTEGER CENTS (100000 = $1,000.00). In Postgres you'd use NUMERIC(12, 2).
Never use FLOAT for money.
"""

import sqlite3

SCHEMA_AND_DATA = """
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    state       TEXT                       -- may be NULL (unknown)
);

CREATE TABLE accounts (
    account_id  INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    type        TEXT NOT NULL CHECK (type IN ('checking', 'savings'))
);

CREATE TABLE transactions (
    txn_id       INTEGER PRIMARY KEY,
    account_id   INTEGER NOT NULL REFERENCES accounts(account_id),
    txn_date     TEXT NOT NULL,            -- ISO dates sort correctly as text
    amount_cents INTEGER NOT NULL          -- + deposit, - withdrawal
);

CREATE TABLE loans (
    loan_id     TEXT PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    officer     TEXT NOT NULL,
    amount      INTEGER NOT NULL CHECK (amount > 0),   -- whole dollars
    status      TEXT NOT NULL
);

INSERT INTO customers VALUES
    (1, 'Ana',  'MA'),
    (2, 'Ben',  'MA'),
    (3, 'Cara', 'NH'),
    (4, 'Dev',  'MA'),     -- has NO accounts
    (5, 'Eli',  NULL);     -- has an account but NO transactions

INSERT INTO accounts VALUES
    (101, 1, 'checking'),
    (102, 1, 'savings'),
    (201, 2, 'checking'),
    (301, 3, 'checking'),
    (501, 5, 'checking');

INSERT INTO transactions VALUES
    (1, 101, '2026-11-01',  100000),
    (2, 101, '2026-11-02',  -20000),
    (3, 101, '2026-11-05',   -5000),
    (4, 102, '2026-11-01',  500000),
    (5, 201, '2026-11-03',   30000),
    (6, 201, '2026-11-03',   30000),   -- duplicate of txn 5
    (7, 301, '2026-11-04',   75000),
    (8, 101, '2026-11-07',   12550);

INSERT INTO loans VALUES
    ('L1', 1, 'Kim', 450000, 'Approved'),
    ('L2', 2, 'Kim', 300000, 'Funded'),
    ('L3', 3, 'Lee', 600000, 'Approved'),
    ('L4', 1, 'Lee', 250000, 'Denied'),
    ('L5', 3, 'Kim', 600000, 'Funded');
"""


def run(conn, label, sql, expected=None):
    """Run a query, print the rows, and check them if `expected` is given."""
    rows = conn.execute(sql).fetchall()
    print(f"\n-- {label}")
    for row in rows:
        print("  ", row)
    if expected is not None:
        assert rows == expected, f"{label}: expected {expected}, got {rows}"
    return rows


def main():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite enforces FKs only when asked
    conn.executescript(SCHEMA_AND_DATA)

    # Q2 INNER vs LEFT JOIN
    run(conn, "Q2 INNER JOIN: only customers WITH accounts", """
        SELECT c.name, a.account_id
        FROM customers c
        JOIN accounts a ON a.customer_id = c.customer_id
        ORDER BY a.account_id
    """, [("Ana", 101), ("Ana", 102), ("Ben", 201), ("Cara", 301), ("Eli", 501)])

    run(conn, "Q2 LEFT JOIN: every customer, NULL where no account", """
        SELECT c.name, a.account_id
        FROM customers c
        LEFT JOIN accounts a ON a.customer_id = c.customer_id
        WHERE c.name IN ('Dev', 'Eli')
        ORDER BY c.name
    """, [("Dev", None), ("Eli", 501)])

    # Q3 customers with no transactions
    run(conn, "Q3 NOT EXISTS: customers with no transactions in ANY account", """
        SELECT c.name
        FROM customers c
        WHERE NOT EXISTS (
            SELECT 1
            FROM accounts a
            JOIN transactions t ON t.account_id = a.account_id
            WHERE a.customer_id = c.customer_id
        )
        ORDER BY c.name
    """, [("Dev",), ("Eli",)])

    run(conn, "Q3 LEFT JOIN + GROUP BY version (same answer)", """
        SELECT c.name
        FROM customers c
        LEFT JOIN accounts a     ON a.customer_id = c.customer_id
        LEFT JOIN transactions t ON t.account_id  = a.account_id
        GROUP BY c.customer_id, c.name
        HAVING COUNT(t.txn_id) = 0
        ORDER BY c.name
    """, [("Dev",), ("Eli",)])

    # Q3 detail: the NOT IN + NULL trap
    conn.executescript("""
        CREATE TABLE blocked (customer_id INTEGER);
        INSERT INTO blocked VALUES (1), (NULL);
    """)
    run(conn, "Q3 TRAP: NOT IN with a NULL in the list returns NOTHING", """
        SELECT name FROM customers
        WHERE customer_id NOT IN (SELECT customer_id FROM blocked)
    """, [])
    run(conn, "Q3 FIX: NOT EXISTS ignores the NULL correctly", """
        SELECT name FROM customers c
        WHERE NOT EXISTS (SELECT 1 FROM blocked b WHERE b.customer_id = c.customer_id)
        ORDER BY customer_id
    """, [("Ben",), ("Cara",), ("Dev",), ("Eli",)])

    # Q4 WHERE vs HAVING, plus conditional aggregation
    run(conn, "Q4 WHERE filters rows, HAVING filters groups", """
        SELECT account_id, SUM(amount_cents) AS deposits_cents
        FROM transactions
        WHERE amount_cents > 0              -- rows: deposits only
        GROUP BY account_id
        HAVING SUM(amount_cents) >= 100000  -- groups: at least $1,000 deposited
        ORDER BY account_id
    """, [(101, 112550), (102, 500000)])

    run(conn, "Q4 conditional aggregation with CASE (deposits vs withdrawals)", """
        SELECT account_id,
               SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END)  AS deposits,
               SUM(CASE WHEN amount_cents < 0 THEN -amount_cents ELSE 0 END) AS withdrawals
        FROM transactions
        WHERE account_id = 101
        GROUP BY account_id
    """, [(101, 112550, 25000)])

    # Q5 COUNT flavors
    run(conn, "Q5 COUNT(*) vs COUNT(col) vs COUNT(DISTINCT col)", """
        SELECT COUNT(*), COUNT(state), COUNT(DISTINCT state) FROM customers
    """, [(5, 4, 2)])

    # Q6 NULL behavior
    run(conn, "Q6 `= NULL` matches nothing", "SELECT name FROM customers WHERE state = NULL", [])
    run(conn, "Q6 `IS NULL` works", "SELECT name FROM customers WHERE state IS NULL", [("Eli",)])
    run(conn, "Q6 COALESCE fills in a default", """
        SELECT name, COALESCE(state, 'Unknown') FROM customers WHERE customer_id = 5
    """, [("Eli", "Unknown")])

    # Q7 running balance
    run(conn, "Q7 running balance per account (ROWS frame)", """
        SELECT account_id, txn_date, amount_cents,
               SUM(amount_cents) OVER (
                   PARTITION BY account_id
                   ORDER BY txn_date, txn_id
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
               ) AS running_balance
        FROM transactions
        WHERE account_id = 101
        ORDER BY txn_date, txn_id
    """, [
        (101, "2026-11-01", 100000, 100000),
        (101, "2026-11-02", -20000, 80000),
        (101, "2026-11-05", -5000, 75000),
        (101, "2026-11-07", 12550, 87550),
    ])

    run(conn, "Q7 DETAIL: default frame (RANGE) lumps same-date rows together", """
        SELECT txn_id,
               SUM(amount_cents) OVER (ORDER BY txn_date) AS default_range,
               SUM(amount_cents) OVER (ORDER BY txn_date
                   ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS rows_frame
        FROM transactions
        WHERE account_id = 201
        ORDER BY txn_id
    """, [(5, 60000, 30000), (6, 60000, 60000)])

    # Q8 ranking functions
    run(conn, "Q8 ROW_NUMBER vs RANK vs DENSE_RANK", """
        SELECT loan_id, amount,
               ROW_NUMBER() OVER (ORDER BY amount DESC, loan_id) AS row_num,
               RANK()       OVER (ORDER BY amount DESC)          AS rnk,
               DENSE_RANK() OVER (ORDER BY amount DESC)          AS dense_rnk
        FROM loans
        ORDER BY amount DESC, loan_id
    """, [
        ("L3", 600000, 1, 1, 1),
        ("L5", 600000, 2, 1, 1),
        ("L1", 450000, 3, 3, 2),
        ("L2", 300000, 4, 4, 3),
        ("L4", 250000, 5, 5, 4),
    ])

    run(conn, "Q8 top loan per officer (top-N per group)", """
        WITH ranked AS (
            SELECT officer, loan_id, amount,
                   ROW_NUMBER() OVER (PARTITION BY officer ORDER BY amount DESC, loan_id) AS rn
            FROM loans
        )
        SELECT officer, loan_id, amount FROM ranked WHERE rn = 1 ORDER BY officer
    """, [("Kim", "L5", 600000), ("Lee", "L3", 600000)])

    # Q9 second highest
    run(conn, "Q9 second-highest loan amount (MAX below MAX)", """
        SELECT MAX(amount) FROM loans WHERE amount < (SELECT MAX(amount) FROM loans)
    """, [(450000,)])
    run(conn, "Q9 Nth highest with DENSE_RANK (N = 2)", """
        SELECT DISTINCT amount FROM (
            SELECT amount, DENSE_RANK() OVER (ORDER BY amount DESC) AS dr FROM loans
        ) WHERE dr = 2
    """, [(450000,)])

    # Q10 LAG
    run(conn, "Q10 LAG: days since the previous transaction", """
        SELECT txn_id, txn_date,
               LAG(txn_date) OVER (PARTITION BY account_id ORDER BY txn_date, txn_id) AS prev_date,
               CAST(julianday(txn_date)
                    - julianday(LAG(txn_date) OVER (PARTITION BY account_id ORDER BY txn_date, txn_id))
                    AS INTEGER) AS days_gap
        FROM transactions
        WHERE account_id = 101
        ORDER BY txn_date
    """, [
        (1, "2026-11-01", None, None),
        (2, "2026-11-02", "2026-11-01", 1),
        (3, "2026-11-05", "2026-11-02", 3),
        (8, "2026-11-07", "2026-11-05", 2),
    ])

    # Q11 recursive CTE
    run(conn, "Q11 recursive CTE: days in Nov 1-7 with NO transactions", """
        WITH RECURSIVE days(d) AS (
            SELECT '2026-11-01'
            UNION ALL
            SELECT date(d, '+1 day') FROM days WHERE d < '2026-11-07'
        )
        SELECT d FROM days
        WHERE d NOT IN (SELECT txn_date FROM transactions)   -- safe: txn_date is NOT NULL
        ORDER BY d
    """, [("2026-11-06",)])

    # Q12 correlated subquery
    run(conn, "Q12 correlated subquery: transactions above their account's average", """
        SELECT t.txn_id, t.account_id, t.amount_cents
        FROM transactions t
        WHERE t.amount_cents > (
            SELECT AVG(t2.amount_cents) FROM transactions t2 WHERE t2.account_id = t.account_id
        )
        ORDER BY t.txn_id
    """, [(1, 101, 100000)])   # account 101 averages $218.88, so only the $1,000 deposit is above it

    # Q13 duplicates
    run(conn, "Q13 find duplicates", """
        SELECT account_id, txn_date, amount_cents, COUNT(*) AS copies
        FROM transactions
        GROUP BY account_id, txn_date, amount_cents
        HAVING COUNT(*) > 1
    """, [(201, "2026-11-03", 30000, 2)])

    # Q14 indexes: SQLite shows whether a query would use the index
    conn.execute("CREATE INDEX idx_txn_account_date ON transactions(account_id, txn_date)")
    plan = conn.execute("""
        EXPLAIN QUERY PLAN
        SELECT * FROM transactions WHERE account_id = 101 AND txn_date >= '2026-11-02'
    """).fetchall()
    plan_text = " ".join(str(step[-1]) for step in plan)
    print("\n-- Q14 plan using the composite index:\n  ", plan_text)
    assert "idx_txn_account_date" in plan_text

    plan = conn.execute("""
        EXPLAIN QUERY PLAN SELECT * FROM transactions WHERE txn_date >= '2026-11-02'
    """).fetchall()
    plan_text = " ".join(str(step[-1]) for step in plan)
    print("-- Q14 plan filtering on the SECOND column only (leftmost-prefix rule):\n  ", plan_text)
    assert "SCAN" in plan_text  # can't seek using the index; scans instead

    # Q16 transactions: all-or-nothing
    try:
        with conn:  # sqlite3 connection as a context manager = one transaction
            conn.execute("INSERT INTO transactions VALUES (9, 101, '2026-11-08', -10000)")
            conn.execute("INSERT INTO transactions VALUES (10, 999, '2026-11-08', 10000)")  # bad account
    except sqlite3.IntegrityError:
        pass
    run(conn, "Q16 failed transfer rolled back BOTH inserts", """
        SELECT COUNT(*) FROM transactions WHERE txn_id IN (9, 10)
    """, [(0,)])

    # Q18 constraints
    try:
        conn.execute("INSERT INTO loans VALUES ('L9', 1, 'Kim', -5, 'Approved')")
        raise AssertionError("CHECK constraint should have rejected a negative loan")
    except sqlite3.IntegrityError as err:
        print(f"\n-- Q18 CHECK constraint rejected a negative loan: {err}")

    # Q19 UNION vs UNION ALL
    run(conn, "Q19 UNION removes duplicates", """
        SELECT officer FROM loans WHERE status = 'Approved'
        UNION
        SELECT officer FROM loans WHERE status = 'Funded'
        ORDER BY officer
    """, [("Kim",), ("Lee",)])
    run(conn, "Q19 UNION ALL keeps them", """
        SELECT COUNT(*) FROM (
            SELECT officer FROM loans WHERE status = 'Approved'
            UNION ALL
            SELECT officer FROM loans WHERE status = 'Funded'
        )
    """, [(4,)])

    # Q20 keyset pagination and upsert
    run(conn, "Q20 keyset pagination: next page after txn_id 4", """
        SELECT txn_id FROM transactions WHERE txn_id > 4 ORDER BY txn_id LIMIT 2
    """, [(5,), (6,)])

    conn.execute("CREATE TABLE processed_events (event_id TEXT PRIMARY KEY)")
    first = conn.execute("INSERT INTO processed_events VALUES ('evt-1') ON CONFLICT DO NOTHING").rowcount
    second = conn.execute("INSERT INTO processed_events VALUES ('evt-1') ON CONFLICT DO NOTHING").rowcount
    print(f"\n-- Q20 idempotent insert: first rowcount={first}, second rowcount={second}")
    assert (first, second) == (1, 0)

    # Q13 delete duplicates, keeping the lowest id (run last: it changes the data)
    conn.execute("""
        DELETE FROM transactions
        WHERE txn_id NOT IN (
            SELECT MIN(txn_id) FROM transactions GROUP BY account_id, txn_date, amount_cents
        )
    """)
    run(conn, "Q13 after deleting duplicates (kept txn 5, removed 6)", """
        SELECT txn_id FROM transactions WHERE account_id = 201
    """, [(5,)])

    print("\nAll queries checked.")


if __name__ == "__main__":
    main()
