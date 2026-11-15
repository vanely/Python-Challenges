# Round 2 — Design, Troubleshooting, and Python/SQL Concepts

```
round_2/
  design/
    00_glossary.md                      <- every technology, explained simply (read first)
    01_loan_status_integration.md       <- Encompass -> internal system -> notify loan officer
    02_ai_paystub_extraction.md         <- LLM pulls fields from pay stubs, safely
    03_troubleshooting_app_crash.md     <- "The VP says the app crashes"
  python/
    top_20_python_questions.md
    python_examples.py                  <- runs every surprising claim in the guide
  sql/
    top_20_sql_questions.md
    sql_examples.py                     <- runs every query in the guide (SQLite, no install)
```

## How to use this

1. Read `design/00_glossary.md` so the terms in the design docs make sense.
2. Practice each design doc **out loud** in 25 minutes. Use the "Interview script" at the top of each one as your outline.
3. For Python and SQL, read one question, then close the file and explain it out loud as if to the interviewer.
4. Run the example scripts and change the code to see what breaks:
   ```bash
   python3 round_2/python/python_examples.py
   python3 round_2/sql/sql_examples.py
   ```

## The shape of every good design answer

1. **Clarify** (2–3 min): who uses it, how much volume, what "done" looks like, any hard rules (compliance, latency).
2. **Draw the simple version** first: boxes and arrows.
3. **Walk the "happy path"**: one event from start to finish.
4. **Then the failure paths**: what if this box is down, slow, or sends the same thing twice?
5. **Name your tradeoffs out loud**: "I picked X over Y because ___; the cost is ___."
6. **Close with operations**: monitoring, alerts, audit, security, cost.

Interviewers care more about **why** you made each choice than about the exact tool names.
