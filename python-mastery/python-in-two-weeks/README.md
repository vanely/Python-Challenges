# Python in Two Weeks — for a TypeScript developer

A 14-day, ~4 hr/day path from "never wrote Python" to "ships typed, idiomatic Python."
Built for someone who already thinks in TypeScript, so every concept is mapped to what you know.
This is Stage 1 of the [roadmap](../README.md). Fourteen days is the fast pace. If you want to keep what you learn, stretch it to 4–6 weeks: give `docpipe` a week of its own, and split Day 11 across two days.

## Daily rhythm

| Block | Time | What |
|---|---|---|
| Concept | 45 min | Read the day's `README.md` summary, then the linked primary sources |
| Copy | 45 min | Type out (never paste) the files in `copy/` — then run them |
| Analyze | 45 min | Read real library source per `codebase-reading/` and answer the prompts |
| Build | 90 min | Do the day's build task; on project days, work on the project |

## Layout

```
week1/
  day01-02-syntax/                     Syntax mapped to TS, comprehensions, unpacking
  day03-data-model/                    dicts/sets, dataclasses, dunders, typing
  day04-iterators-generators-decorators/
  day05-tooling/                       uv, pytest, ruff, mypy, project layout
  day06-07-project1-cli/               Project 1 (guided): `fetchr` — typed CLI that hits an API
week2/
  day08-async/                         asyncio, httpx, GIL, threads vs processes
  day09-errors-logging-files/          exceptions, logging, pathlib, subprocess, json/csv
  day10-fastapi/                       FastAPI + Pydantic API
  day11-data-sql/                      polars, sqlite3, SQLAlchemy basics
  day12-14-project2-docpipe/           Project 2 (guided): PDF -> chunks -> SQLite full-text search -> FastAPI
codebase-reading/                      Guided reading of rich / httpx / typer, one chunk per day
```

## Setup (do this once, Day 1)

Windows, in Git Bash:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # uv: package + venv manager (like pnpm + nvm)
export PATH="$HOME/.local/bin:$PATH"                 # also add this to ~/.bashrc
uv python install 3.12
cd week1/day01-02-syntax && uv venv                  # picks 3.12 from ../../../.python-version
source .venv/Scripts/activate                        # macOS/Linux: source .venv/bin/activate
uv pip install pytest ruff mypy
python --version                                     # Python 3.12.x
```

On macOS/Linux, install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`.

`day05-tooling` and `day10-fastapi` each have a `pyproject.toml`. Run `uv sync` inside the folder, then `uv run pytest`, `uv run mypy src` and so on. With `uv run` you don't need to activate anything.

The two projects, `fetchr` and `docpipe`, are **guided builds**. You create the project yourself with `uv init --package`, then work through `steps/01-…` to `steps/05-…`:
- each step explains the concepts, gives you code to type, and leaves one part for you to write;
- a test suite you didn't write (`checkpoints/`) checks each step;
- a finished, tested solution sits in `reference/`. Open it only after your checkpoints pass, then diff it against your code.

## After this

Next is Stage 2, [`../django-and-drf/`](../django-and-drf/README.md): Django and DRF as four guided projects that build one issue tracker. The FastAPI and SQLAlchemy days (10–11) are the foundation it builds on. The [roadmap](../README.md) shows how the stages fit together.

## Primary sources used throughout

- Official tutorial: https://docs.python.org/3/tutorial/
- Library reference: https://docs.python.org/3/library/
- PEP 8 (style): https://peps.python.org/pep-0008/
- PEP 20 (Zen): https://peps.python.org/pep-0020/
- *Fluent Python*, 2nd ed., Luciano Ramalho (O'Reilly, 2022) — chapters referenced per day
- Real Python: https://realpython.com — article titles are given; search by title, since URLs drift

## Rules of the road

1. `mypy --strict` and `ruff check` pass before you call anything done.
2. Type out the `copy/` files by hand. The point is finger memory of the syntax.
3. If you catch yourself writing a `class` where a dict or dataclass would do, or a `for` loop that builds a list, stop — that's TS leaking in.
