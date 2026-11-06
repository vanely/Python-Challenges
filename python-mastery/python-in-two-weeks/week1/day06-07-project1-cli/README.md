# Day 6–7: Project 1 — `fetchr`, a typed CLI that hits an API (guided)

A CLI that fetches GitHub repository data, caches it locally, and renders it as a table or JSON:

```
fetchr repo encode/httpx                         # one repo: stars, forks, open issues, language
fetchr repos encode/httpx pallets/flask --sort stars --json
fetchr issues encode/httpx --limit 20 --state open
fetchr cache clear
```

It uses everything from Week 1: dataclasses, typing, enums, generators, context managers, decorators, pathlib, JSON, tests, and the full toolchain. It uses the public GitHub REST API; no token is needed for light use, and setting `GITHUB_TOKEN` raises the rate limit.

You build it in five guided steps. Each one explains the mechanism, has you type part of the code, has you write a part yourself from a spec ("Your turn"), and then checks you with tests you didn't write.

| Step | File | You build | Checkpoint | Time |
|---|---|---|---|---|
| 1 | [steps/01-scaffold-and-models.md](steps/01-scaffold-and-models.md) | Package layout, `pyproject.toml`, `Repo`/`Issue` models | `test_fx_01_models.py` | ~1.5 h |
| 2 | [steps/02-cache.md](steps/02-cache.md) | A JSON file cache with TTL, plus a `@cached` decorator | `test_fx_02_cache.py` | ~1.5 h |
| 3 | [steps/03-client.md](steps/03-client.md) | `GitHubClient`: context manager, testable transport, lazy pagination | `test_fx_03_client.py` | ~2 h |
| 4 | [steps/04-cli.md](steps/04-cli.md) | typer commands, enum options, rich tables, JSON output | `test_fx_04_cli.py` | ~1.5 h |
| 5 | [steps/05-harden.md](steps/05-harden.md) | Every failure becomes one clean line and exit code 1; your own tests; ruff and mypy | `test_fx_05_errors.py` | ~1.5 h |

That's ~8 hours: two full days at the course's 4 h/day. If it takes longer, take longer. Don't skip the "Explain it back" questions; answer them in `NOTES.md` next to this README.

## Setup

```bash
cd week1/day06-07-project1-cli
uv init --package fetchr            # creates fetchr/ with a src/ layout
cd fetchr
```

Step 1 replaces the generated `pyproject.toml` and explains every line of it. From then on, run everything from `fetchr/`:

```bash
uv run pytest ../checkpoints/test_fx_01_models.py     # one step's checkpoint
uv run pytest ../checkpoints                          # all of them; only once every step is done
```

The checkpoints are the spec. When you're stuck, read the failing test. Don't edit them.

Before the last step, run one checkpoint file at a time. Later checkpoint files import modules you haven't written yet, and pytest aborts the *whole* run when collection fails, so `../checkpoints` reports an error rather than "01–03 pass". Also, because the test paths point outside `fetchr/`, pytest ignores the `[tool.pytest.ini_options]` in your `pyproject.toml` for checkpoint runs. That only affects your own `uv run pytest`.

## Readings

| Source | Where | Read |
|---|---|---|
| typer | https://typer.tiangolo.com/tutorial/ | First steps → Commands → Options → Arguments; "Enum - Choices" |
| httpx | https://www.python-httpx.org/quickstart/ | Quickstart; Advanced → Clients; Advanced → Transports (`MockTransport`) |
| `json` | https://docs.python.org/3/library/json.html | `dumps`/`loads`, `indent`, `default=` |
| `pathlib` | https://docs.python.org/3/library/pathlib.html | `/`, `read_text`, `mkdir(parents=True, exist_ok=True)`, `stat` |
| rich | https://rich.readthedocs.io/en/stable/tables.html | Tables + Console |
| GitHub REST | https://docs.github.com/en/rest/repos/repos#get-a-repository | Response shape; "Rate limits for the REST API"; "Using pagination in the REST API" |

## Reference implementation

`reference/fetchr/` is a complete, tested solution. **Open it only after all five checkpoints pass for your version.** Then diff it against yours file by file and write down every difference in `NOTES.md`: which version is better, and why. The reference is ~350 lines of source. If yours is three times that, look for TypeScript habits.

```bash
cd reference/fetchr && uv sync && uv run fetchr --help
uv run pytest && uv run ruff check . && uv run mypy src tests
```
