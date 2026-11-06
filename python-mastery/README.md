# Python, from TypeScript developer to mastery

Three stages, done in order. Each one assumes the one before it.

| Stage | Folder | You start as | You finish able to | Honest time |
|---|---|---|---|---|
| 1 | [`python-in-two-weeks/`](python-in-two-weeks/README.md) | A TypeScript developer who has never written Python | Write typed, idiomatic Python; ship a CLI and a FastAPI service with tests | 2 weeks at 4 h/day if you've done this kind of thing before; 4–6 weeks if you want to keep it |
| 2 | [`django-and-drf/`](django-and-drf/README.md) | Stage 1 graduate | Build and ship a Django + DRF backend: ORM without N+1s, transactions, permissions, a documented API, production settings | ~42 h of guided projects; 5–6 weeks at 8–10 h/week |
| 3 | [`python-mastery/`](python-mastery/README.md) | Stage 2 graduate, or someone who already ships production Django | Explain and bend the runtime: descriptors, metaclasses, typing, async cancellation, profiling, packaging, bytecode, the GIL, your own ASGI framework | 9–12 months at 8–10 h/week; Tiers 4–5 never really end |

Why this order: Stage 3's first module opens with "you've used `class Article(models.Model)` a thousand times" and then shows you how Django's metaclass makes that work. That only lands once Stage 2 has had you write models, querysets and serializers for real. Stage 2 in turn assumes Stage 1's typing, `pytest` and `uv` habits.

## How to work, all stages

1. **Feedback before progress.** Every stage has tests you didn't write: Stage 1's exercises and project suites, Stage 2's `checkpoints/`, and Stage 3's project test suites. Don't move on while they're red.
2. **Write the explanation down.** Each stage has a `NOTES.md` or journal. Fill in the day's or step's answers before starting the next one. If you can't explain something without re-reading, you haven't learned it yet.
3. **Reference implementations come last.** Where a finished solution exists (Stage 1 projects, Stage 3 projects), open it only after your own version passes. Stage 2 deliberately ships none.
4. **Copying is for syntax, not understanding.** Typing out `copy/` files is useful for the first few days of Stage 1. After that, read each file, predict its output, then run it. Break it on purpose and predict the error.

## Setup (once, Windows + Git Bash)

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # installs uv
export PATH="$HOME/.local/bin:$PATH"     # add this line to ~/.bashrc too
uv python install 3.12
uv run python --version                  # from inside python-mastery/: Python 3.12.x
```

`python-mastery/.python-version` pins **Python 3.12** for loose scripts and for `uv venv`/`uv init` anywhere below it. `uv init` copies the pin into each new project. Projects are a separate case: inside a folder with a `pyproject.toml`, uv only reads a `.python-version` in *that* folder and otherwise picks the newest Python allowed by `requires-python`. That's why every project in the course ships its own `.python-version`. If you create a project by hand, run `uv python pin 3.12` in it. Each project folder has its own `pyproject.toml`: run `uv sync` there once, then use `uv run <cmd>` (`uv run pytest`, `uv run mypy src`). You never have to activate a virtualenv. If you want to activate one anyway, it's `source .venv/Scripts/activate` on Windows and `source .venv/bin/activate` on macOS/Linux.

On macOS/Linux, install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`; everything else is the same.

A few Stage 3 experiments need other interpreters (`uv python install 3.13t` for free-threading, `3.10` for a bytecode comparison). Each one says so where it's needed, and you run it with `uv run --python 3.13t ...` without changing the pin.
