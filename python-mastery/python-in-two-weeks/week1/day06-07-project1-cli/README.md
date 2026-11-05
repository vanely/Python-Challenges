# Day 6–7: Project 1 — `fetchr`, a typed CLI that hits an API

A CLI that fetches GitHub repository data, caches it locally, and renders it as a table or JSON.
It exercises everything from Week 1: dataclasses, typing, generators, context managers, decorators,
argparse/typer, pathlib, JSON, tests, and the full toolchain.

## What you'll build
```
fetchr repo encode/httpx                # one repo: stars, forks, open issues, language
fetchr repos encode/httpx pallets/flask --sort stars --json
fetchr issues encode/httpx --limit 20 --state open
fetchr cache clear
```
Uses the public GitHub REST API (no token needed for light use; set `GITHUB_TOKEN` to raise the rate limit).

## Readings for the project

| Source | Where | Read |
|---|---|---|
| typer | https://typer.tiangolo.com/tutorial/ | First steps → Commands → Options → Arguments |
| argparse (know it exists; stdlib alternative) | https://docs.python.org/3/library/argparse.html | Skim `add_argument` |
| httpx | https://www.python-httpx.org/quickstart/ | Quickstart; "Advanced → Clients" |
| `json` | https://docs.python.org/3/library/json.html | `dumps`/`loads`, `indent`, `default=` |
| `pathlib` | https://docs.python.org/3/library/pathlib.html | Basics: `/` operator, `read_text`, `mkdir(parents=True, exist_ok=True)` |
| rich | https://rich.readthedocs.io/en/stable/tables.html | Tables + console |
| GitHub REST | https://docs.github.com/en/rest/repos/repos#get-a-repository | Response shape |

Key points:
- **typer** turns a typed function into a CLI: parameters become args/options, annotations become validation, docstrings become `--help`. It's built on click. `typer.Typer()` groups subcommands.
- **httpx** is `requests` with a modern API, HTTP/2, and async support (Day 8). Use a `Client` as a context manager for connection reuse; `raise_for_status()` turns 4xx/5xx into exceptions.
- **rich** does terminal tables/colors. `Console().print(table)`.

## Build plan

### Day 6 (build the core, ~3 hrs)
1. `uv init --lib fetchr` — or copy this folder's skeleton. `uv add httpx typer rich` and dev deps.
2. `models.py`: `Repo` and `Issue` frozen dataclasses with a `from_api(dict)` classmethod each. `TypedDict`s for the raw API shape.
3. `cache.py`: a JSON file cache keyed by URL with TTL. Implement as a class with `get`/`set`, and a `@cached(ttl=...)` decorator that uses it.
4. `client.py`: `GitHubClient` context manager wrapping `httpx.Client`; methods `repo(owner, name) -> Repo`, `issues(owner, name, state, limit) -> Iterator[Issue]` — the issues method should **paginate lazily with a generator** (`per_page=100`, follow the `Link` header or increment `page` until an empty page).
5. `cli.py`: typer app with `repo`, `repos`, `issues`, `cache clear`. `--json` flag switches output.

### Day 7 (harden and finish, ~3 hrs)
6. `render.py`: rich tables; a `to_json(objs)` that handles dataclasses via `dataclasses.asdict`.
7. Tests: unit-test models with fixture dicts; test the cache with `tmp_path`; test the client by monkeypatching `httpx.Client.get` (no network in tests); test the CLI with `typer.testing.CliRunner`.
8. `ruff`, `mypy --strict`, `pytest` all green. `uv run fetchr repo encode/httpx` works.
9. Stretch: `--sort` with `Literal["stars","forks","issues"]`; retry decorator from Day 4 on network calls; `--since` date filter on issues using `datetime.fromisoformat`.

## Reference implementation
`fetchr/` contains a complete, tested solution. **Build yours first**, then diff against it. The reference is ~300 lines — if yours is 3× that, you're writing TS in Python.

Run the reference:
```bash
cd fetchr && uv sync && uv run fetchr --help
uv run pytest && uv run ruff check . && uv run mypy src
```
