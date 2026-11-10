# Day 11: Data tooling — polars, sqlite3, SQLAlchemy

Even if you never do "data science," this is where Python dominates and you'll be handed a CSV or a DataFrame sooner than you think.

## Objectives
- Do the 80% of dataframe work (load, filter, group, join, write) in polars
- Use `sqlite3` directly, safely (parameterised queries, transactions, context managers)
- Know enough SQLAlchemy Core/ORM to read a codebase that uses it

## Readings

| Source | Where | Read |
|---|---|---|
| polars user guide | https://docs.pola.rs/user-guide/ | Getting started; Concepts → Expressions, Contexts (select/filter/group_by/with_columns), Lazy API |
| polars vs pandas | https://docs.pola.rs/user-guide/migration/pandas/ | Skim — you'll see pandas everywhere; know the mapping |
| sqlite3 | https://docs.python.org/3/library/sqlite3.html | Tutorial; "How-to guides" → placeholders, transactions, `Row` factory |
| SQLAlchemy | https://docs.sqlalchemy.org/en/20/tutorial/ | Unified tutorial: Establishing Connectivity → Working with Data (Core); then ORM "Declarative" quickstart |
| SQLAlchemy ORM quickstart | https://docs.sqlalchemy.org/en/20/orm/quickstart.html | All |
| Real Python | "Python Polars: A Lightning-Fast DataFrame Library" | All |

## Reading summaries

### polars (over pandas, for new code)
- `pl.read_csv / read_parquet / read_json`, `pl.DataFrame({...})`. `df.write_csv(...)`.
- **Expressions** are the unit: `pl.col("price") * pl.col("qty")`. Compose them; they're lazy and parallel.
- **Contexts** you'll use: `select` (choose/compute columns), `filter`, `with_columns` (add/replace), `group_by(...).agg(...)`, `sort`, `join(other, on=..., how=...)`.
- Strings/dates via namespaces: `pl.col("s").str.to_lowercase()`, `pl.col("d").dt.year()`.
- `df.lazy()...collect()` — build a query plan, optimise, run. Use `scan_csv` for big files.
- No index (unlike pandas). No `SettingWithCopyWarning`. Strict types.
- Mapping from TS: think of a DataFrame as a typed columnar table; expressions are like a query builder; `group_by/agg` ≈ SQL.
- pandas equivalents: `df[df.x > 1]` → `df.filter(pl.col("x") > 1)`; `df.groupby("k").sum()` → `df.group_by("k").agg(pl.all().sum())`; `df.assign(y=...)` → `df.with_columns(y=...)`.

### sqlite3
- `sqlite3.connect(path)` → connection; `with conn:` commits on success / rolls back on exception (**it doesn't close** — use `contextlib.closing` or close manually).
- **Always** parameterise: `cur.execute("... WHERE id = ?", (id,))` or `:name` style. Never f-string SQL.
- `conn.row_factory = sqlite3.Row` → rows act like dicts. `executemany` for bulk inserts. `executescript` for DDL.
- `PRAGMA journal_mode=WAL` and `foreign_keys=ON` at connect time. `:memory:` for tests.
- FTS5 virtual tables give you full-text search for free — used in Project 2.

### SQLAlchemy 2.0
- **Core**: `create_engine`, `Table`/`Column` or `select(...)`, `engine.begin()` for a transaction, `conn.execute(stmt)`. Portable SQL builder.
- **ORM**: `class Base(DeclarativeBase)`, `class Note(Base): __tablename__ = ...; id: Mapped[int] = mapped_column(primary_key=True)`. `Session` for unit of work; `session.add`, `session.scalars(select(Note).where(...))`, `session.commit()`.
- Relationships: `relationship()` + `ForeignKey`. Lazy loading by default — the N+1 trap; use `selectinload`.
- Migrations are a separate tool: Alembic.
- When to skip it: small scripts, one table, SQLite → `sqlite3` directly is fine and clearer.

## Copy
`copy/01_polars.py` → `copy/02_sqlite.py` → `copy/03_sqlalchemy.py`

## Analytical reading
`codebase-reading/README.md`, Day 11 (`sqlite3/__init__.py` context manager; polars expression API surface).

## Build task (90 min)
`steps/01-sqlite-repo.md` then `steps/02-report.md`. Checkpoints import `notesql` from the project you run pytest in. `reference/notesql/` is the finished store and report; open it after `uv run pytest ../checkpoints` passes.

The same `SqliteRepo` can implement Day 10's `NoteRepo` protocol. Override `get_repo` in the Day 10 tests with `SqliteRepo(":memory:")` and keep those tests green.
