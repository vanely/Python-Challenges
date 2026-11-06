# Day 5: Tooling — uv, pyproject, pytest, ruff, mypy, project layout

## Objectives
- Stand up a Python project the way a modern team would, in under 5 minutes
- Know the pytest idioms you'll use 95% of the time
- Understand `import` and packaging well enough to never fight `ModuleNotFoundError` again

## Readings

| Source | Where | Read |
|---|---|---|
| uv docs | https://docs.astral.sh/uv/ | "Getting started", "Projects", "Running scripts" |
| Python Packaging User Guide | https://packaging.python.org/en/latest/tutorials/packaging-projects/ | Whole tutorial (pyproject.toml, src layout) |
| PEP 621 | https://peps.python.org/pep-0621/ | Skim: the `[project]` table |
| pytest | https://docs.pytest.org/en/stable/how-to/fixtures.html and .../how-to/parametrize.html | Fixtures + parametrize |
| ruff | https://docs.astral.sh/ruff/ | "Configuring Ruff", rule categories list |
| mypy | https://mypy.readthedocs.io/en/stable/getting_started.html | Getting started; "The mypy configuration file" |
| Modules tutorial | https://docs.python.org/3/tutorial/modules.html | 6.1–6.4 (import forms, packages, `__init__.py`) |
| Real Python | "Python Application Layouts"; "Effective Python Testing With Pytest" | Both |
| Source | `httpx` repo: `pyproject.toml`, `httpx/__init__.py`, `tests/conftest.py` | https://github.com/encode/httpx |

## Reading summaries

### The toolchain, mapped
| Need | TS | Python (2026) |
|---|---|---|
| Runtime version manager | nvm / volta | `uv python install 3.12` |
| Package manager + lockfile | pnpm + `package.json` + lockfile | `uv` + `pyproject.toml` + `uv.lock` |
| Isolated deps | `node_modules` | `.venv/` (activate, or just `uv run`) |
| Linter + formatter | eslint + prettier | `ruff check` + `ruff format` (one tool, Rust, instant) |
| Type checker | tsc | `mypy --strict` (or `pyright`) |
| Test runner | vitest / jest | `pytest` |
| Run a script with deps | `npx tsx` | `uv run script.py` (inline deps via PEP 723 header) |
| Publish | npm publish | `uv build && uv publish` |

### `pyproject.toml` = `package.json` + all the config files
One file for metadata, deps, scripts, and tool config (`[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`). See `pyproject.toml` in this folder — it's your template.

`[project.scripts]` maps a command name to `module:function` — that's your CLI entry point after `uv pip install -e .`.

### Layout: src layout
```
myproj/
  pyproject.toml
  src/myproj/__init__.py
  src/myproj/cli.py
  tests/test_cli.py
```
`src/` prevents the classic bug where tests import the working directory instead of the installed package. Install in editable mode (`uv sync` does this) and imports are `from myproj.cli import main` from anywhere.

### Imports
- `import x`, `from x import y`, `from x import y as z`. No default exports. No file extensions.
- A directory with `__init__.py` is a package; `__init__.py` can be empty or re-export the public API.
- Absolute imports (`from myproj.util import f`) always. Relative (`from .util import f`) only inside a package, sparingly.
- `if __name__ == "__main__":` guards script code so importing the module doesn't run it.
- `python -m pkg.module` runs a module as a script, with the current directory on `sys.path` and `__package__` set (so relative imports work). Prefer it over `python path/to/file.py`.
- `ModuleNotFoundError` is almost always: (a) not installed in *this* venv, (b) running from the wrong directory without src layout, (c) a typo in `__init__.py` re-exports.

### pytest — the 95%
- Any `test_*.py` file; any `test_*` function; plain `assert`. No `expect(x).toBe(y)`.
- `pytest -x` stop at first fail; `-k name` filter; `-v` verbose; `--lf` last failed; `-s` show prints.
- **Fixtures** = dependency injection by argument name. `@pytest.fixture def client(): ...` then `def test_x(client):`. `tmp_path` and `monkeypatch` and `capsys` are built in. `conftest.py` shares fixtures across a directory.
- **Parametrize**: `@pytest.mark.parametrize("a,b,out", [(1,2,3),(2,2,4)])` — table-driven tests.
- `pytest.raises(ValueError, match="bad")` for exceptions. `pytest.approx` for floats.
- Mocking: `monkeypatch.setattr(module, "fn", fake)`; `unittest.mock.patch` for the heavier cases.

### ruff
Replaces flake8, isort, pyupgrade, black. Enable `E, F, I, UP, B, SIM` to start. `ruff check --fix` autofixes imports/upgrades. `ruff format` is black-compatible. Add `--select ALL` later and prune once you know what's noise.

### mypy
`--strict` from day one: it forces `-> None`, no implicit `Any`, no untyped defs. Third-party libs without stubs: `ignore_missing_imports` per module, or install `types-*` packages. Escape hatch: `# type: ignore[code]` — always include the error code.

## Copy
`pyproject.toml` and `test_examples.py` in this folder. Then run:
```bash
uv init --lib demo && cd demo && uv add --dev pytest ruff mypy
```
and reproduce the layout above by hand.

## Analytical reading
`codebase-reading/README.md`, Day 5 (`httpx` project structure and `conftest.py`).

## Build task (90 min)
Convert Day 2's `wordfreq.py` and Day 4's build outputs into a proper package `toolbox/` with src layout, `[project.scripts]` entry `wordfreq = "toolbox.wordfreq:main"`, argparse instead of hand-parsing, tests with `tmp_path` fixtures, and a `Makefile`/`justfile` with `lint`, `typecheck`, `test` targets. Everything green. This is the skeleton you'll reuse for both projects.
