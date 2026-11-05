# 0.5 — Packaging and release engineering

Django apps are deployed, not published. This module is everything between "works on my machine" and `pip install yourthing`.

## Objectives
- Build a modern package: `pyproject.toml` (PEP 621), src layout, `py.typed`, entry points, optional extras, dynamic version from git tags
- Test across Python versions with `nox`; lint/type/test in GitHub Actions; publish to TestPyPI then PyPI via trusted publishing (no API tokens in secrets)
- Understand wheels vs sdists, ABI tags, `MANIFEST`-free inclusion rules, and what `pip install -e .` actually does
- Version and change-log discipline: SemVer, `CHANGELOG.md`, deprecation policy

## Readings

| Source | Where | Read |
|---|---|---|
| Python Packaging User Guide | https://packaging.python.org/en/latest/ | "Packaging Python Projects" tutorial; "Writing your pyproject.toml"; "Packaging and distributing projects" (specifically: versioning, extras, entry points) |
| PEP 621 / 517 / 518 / 660 | peps.python.org | 621 (metadata) fully; 517/518 (build backends) skim; 660 (editable installs via backend) skim |
| PEP 427 (wheels) | https://peps.python.org/pep-0427/ | File format + tags. Then https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/ |
| PEP 561 (`py.typed`) | https://peps.python.org/pep-0561/ | All — how type checkers find your types |
| hatchling docs | https://hatch.pypa.io/latest/config/build/ | Build config, file inclusion, `[tool.hatch.version]` |
| uv: publishing | https://docs.astral.sh/uv/guides/publish/ | `uv build`, `uv publish`, trusted publishing |
| nox | https://nox.thea.codes/en/stable/ | Tutorial + "Configuration & API" |
| PyPI trusted publishers | https://docs.pypi.org/trusted-publishers/ | All |
| `pypa/gh-action-pypi-publish` | https://github.com/pypa/gh-action-pypi-publish | README |
| SemVer | https://semver.org | All (short) |
| Keep a Changelog | https://keepachangelog.com | All (short) |
| Hynek Schlawack, "Testing & Packaging" | https://hynek.me/articles/testing-packaging/ | Why src layout |
| Source | `pypa/packaging` → `packaging/tags.py`, `packaging/version.py`; `httpx`'s `pyproject.toml` + `.github/workflows` | See how a real library configures CI + release |

## Reading summaries

### The one file
`pyproject.toml` holds: `[build-system]` (which backend builds you: hatchling/setuptools/flit/pdm/maturin), `[project]` (PEP 621 metadata: name, version or `dynamic = ["version"]`, `requires-python`, `dependencies`, `optional-dependencies`, `scripts`, `classifiers`, `urls`), and `[tool.*]` (ruff, mypy, pytest, coverage, hatch). Dev-only deps go in `[dependency-groups]` (PEP 735) — not in `optional-dependencies`, which are for users.

### sdist vs wheel
- **sdist** (`.tar.gz`): source + `pyproject.toml`; pip must *build* it on the user's machine (needs a compiler for C extensions).
- **wheel** (`.whl`): a zip of the built package with metadata; installation is just unzip. Tags encode compatibility: `py3-none-any` (pure Python), `cp312-cp312-manylinux_2_28_x86_64` (CPython 3.12 ABI, Linux glibc ≥2.28, x86-64). Ship both. For extensions, build wheels per platform with `cibuildwheel` (Tier 2).
- `pip install -e .` (PEP 660): the backend writes a `.pth` file or import hook pointing at your `src/`; edits are live; **`console_scripts` entry points are regenerated only on reinstall**.

### src layout, `py.typed`, inclusion
- `src/pkg/` means tests run against the *installed* package, not the working directory, so packaging bugs surface in CI.
- Ship `src/pkg/py.typed` (empty file) so mypy/pyright use your inline types. Without it, downstream sees `Any`.
- hatchling includes everything under the package by default and respects `.gitignore`; use `[tool.hatch.build.targets.sdist]` `include/exclude` when you must.

### Versioning
- SemVer: MAJOR (breaking), MINOR (features), PATCH (fixes). Pre-releases `1.0.0rc1`; PEP 440 governs Python's exact grammar (`packaging.version.Version` parses it).
- Single source of truth: either `__version__` read by the backend, or **derived from git tags** (`hatch-vcs` / `setuptools-scm`) so a release is `git tag v1.2.0 && git push --tags` and CI does the rest.
- Deprecate before removing: `warnings.warn("...", DeprecationWarning, stacklevel=2)` for at least one MINOR; document in CHANGELOG under "Deprecated".

### nox
A `noxfile.py` with sessions (`tests`, `lint`, `typecheck`, `docs`), each in its own venv, parametrised over Python versions. `nox -s tests-3.12`. It's `tox` with Python instead of INI; `uv` as the backend makes it fast (`nox.options.default_venv_backend = "uv"`).

### CI + release (GitHub Actions)
- `ci.yml`: matrix over OS × Python; `uv sync`, `ruff check`, `ruff format --check`, `mypy`, `pytest --cov`; cache uv.
- `release.yml`: on tag `v*`: `uv build`, upload artifacts, then `pypa/gh-action-pypi-publish` with `id-token: write` permission and an `environment: pypi` that's registered as a **trusted publisher** on PyPI. No secrets.
- TestPyPI first, always: `uv publish --publish-url https://test.pypi.org/legacy/`.

## Copy
`pkgtemplate/` — a complete, buildable, CI-ready package. Type out `pyproject.toml`, `noxfile.py`, and both workflows; read every key. Then:
```bash
cd pkgtemplate && uv sync && uv run nox -s lint typecheck tests
uv build && ls dist/          # sdist + wheel
python -m venv /tmp/clean && /tmp/clean/bin/pip install dist/*.whl && /tmp/clean/bin/pkgtemplate hello
```

## Analysis prompts
1. `unzip -l dist/*.whl`: what's in `*.dist-info/`? Read `METADATA`, `RECORD`, `entry_points.txt`. Where did each come from in `pyproject.toml`?
2. After `pip install -e .`, find the `.pth` file (or `__editable__` finder) in `site-packages`. Read it. Explain how `import pkgtemplate` resolves.
3. In `packaging/tags.py`, trace how `sys_tags()` decides your interpreter's compatible tags. Why does `manylinux` need a glibc version?
4. Pick a dependency of yours with a `.pyi` stubs package (`types-requests`, `django-stubs`). Why does it exist as a separate package instead of `py.typed` upstream?

## Build
Publish `typed_utils` (from 0.2) to **TestPyPI** using this template: src layout, `py.typed`, version from git tag, nox across 3.12/3.13, CI green, trusted publishing configured, `CHANGELOG.md` with `0.1.0`. Install it in a clean venv from TestPyPI and use it from a script with `mypy --strict` seeing the types. Then cut `0.1.1` with a deprecation to practise the cycle.
