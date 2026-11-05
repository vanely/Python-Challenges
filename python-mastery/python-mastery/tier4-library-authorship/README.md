# Tier 4 — Library authorship and upstream contribution (8+ weeks, then ongoing)

You've built things that run once. Now build something *other people import*, keep it working across Python versions and platforms, and get code merged into a project you depend on. This tier has no copy files — the material is your own code, the maintainers' review, and the release process.

## Part A — Publish a real library (weeks 1–5)

### Pick the library
Take one of the things you built and make it real. Good candidates, in order of how much you'll learn:
1. **`microasgi`** — the smallest useful web framework, with pydantic parameter injection. You'll learn API stability under real use.
2. **`fetchd`** (Tier 0.3) as an async rate-limited HTTP fetch library with a typed public API and a CLI.
3. **A Django/DRF package** that scratches an itch from your production work (a field type, a DRF renderer, a management command, a `django-stubs`-clean typed queryset helper). Django packaging has extra constraints (app config, migrations, settings) — good complexity.

### The bar
| Requirement | Tool / doc |
|---|---|
| src layout, `pyproject.toml` only, `py.typed` | Tier 0.5 template |
| 100 % typed public API; `mypy --strict` and pyright both clean | pyright catches different things — run both in CI |
| Tests on every supported version, three OSes | `nox -s tests-3.10 … tests-3.14t`, GitHub Actions matrix |
| Free-threading compatibility statement | test under `3.13t`/`3.14t`; declare `Free-threading` classifier or document why not |
| Docs site with API reference from docstrings | `mkdocs-material` + `mkdocstrings`, or Sphinx + `autodoc2` |
| Changelog per release, semver, deprecation policy | `towncrier` fragments; see *Deprecation* below |
| Wheels for every platform if you have a native extension | `cibuildwheel`; else pure wheel + sdist |
| Trusted publishing, signed provenance | PyPI OIDC (Tier 0.5 `release.yml`); PEP 740 attestations |
| Reproducible dev environment | `uv lock`; `uv run nox` |
| 90 %+ coverage, property tests for the core | `pytest-cov`, `hypothesis` |

### Deprecation policy (write it down in `CONTRIBUTING.md`)
Copy the shape of Django's: deprecate in version N with a `DeprecationWarning` (`warnings.warn(..., stacklevel=2)`), keep working through N+1, remove in N+2. Provide the replacement in the same release you deprecate. Test the warning with `pytest.warns`. Never change behaviour silently in a minor.

### Readings
- Python Packaging User Guide, all of "Guides" — https://packaging.python.org
- "Hypermodern Python" (Claudio Jolowicz) — the whole series; dated in tool choice (poetry → uv) but the *reasoning* is the point
- Hynek Schlawack: "Testing & Packaging", "Semantic Versioning Will Not Save You", "Subclassing in Python Redux" — https://hynek.me/articles/
- `attrs` and `structlog` repos as exemplars of a maintained library: read `CONTRIBUTING.md`, `noxfile.py`/`tox.ini`, `.github/workflows`, `docs/`, `changelog.d/`
- Django's deprecation timeline docs — https://docs.djangoproject.com/en/stable/internals/deprecation/
- `hypothesis` docs "Quickstart" and "Stateful testing"
- PEP 740 (attestations), PEP 735 (dependency groups), PEP 751 (lock files)

### Deliverable
A public repo, ≥3 tagged releases on (Test)PyPI with a changelog that shows one deprecation cycle carried through, CI green on the full matrix, docs published. `NOTES.md`: what broke on 3.13t, on Windows, and what you'd design differently now that the API is frozen.

## Part B — Contribute upstream (weeks 4–8, overlapping)

Merged code in a project you use is the fastest feedback loop available, because the reviewer has context you don't.

### Choosing a project and an issue
- **Django** — `easy pickings` label on Trac; docs and tests PRs are very welcome; you know the codebase already. Read `docs/internals/contributing/` fully first.
- **DRF**, **httpx/starlette/uvicorn** (encode), **pydantic**, **polars-py**, **typeshed** (stubs — a great first PR: fix a wrong stub you hit under `mypy --strict`), **mypy** itself, **CPython** (`easy` label on GitHub; docs/tests first; read the devguide).
- Pick an issue you've *actually hit*. Motivation survives the review cycle; curiosity doesn't always.

### Playbook
1. Fork, build from source, run the full test suite locally *before* changing anything. Note how long it takes and how it's structured — that's a lesson in itself.
2. Reproduce the bug with a failing test first. Commit that alone.
3. Fix. Keep the diff minimal; resist refactoring around it.
4. Read three recently merged PRs in the same area to match conventions (commit style, changelog fragment, docs).
5. Open the PR with: what/why, the test, and any behaviour question you're unsure about, phrased as a question.
6. Respond to review within a day. Don't argue style; do push back with evidence on correctness.
7. After merge: read the release notes when it ships. You are now on the hook for that code.

### Readings
- Python Developer's Guide — https://devguide.python.org (all of "Getting started" and "Development workflow", even if you don't target CPython)
- Django "Contributing to Django" — https://docs.djangoproject.com/en/stable/internals/contributing/
- "How to Contribute to Open Source" (GitHub guide) — skim
- Read the whole thread of one contentious CPython PR or a discuss.python.org PEP thread end to end, to see how decisions get made (suggestions: PEP 703 discussion; PEP 695 syntax debate)

### Deliverable
One merged PR (docs or stubs count). One PR with a *substantive* code change, merged or in review with at least one round addressed. `NOTES.md`: what the reviewer caught that you missed.

## Part C — Release engineering for a native extension (optional, 2 weeks)
Take `tier2-runtime-performance/rust-ext/` to a release: `maturin` + `cibuildwheel` (or `maturin-action`) building manylinux/musllinux/macOS-universal2/Windows wheels, abi3 vs per-version, `sdist` that builds without Rust preinstalled failing *gracefully*, and a free-threaded wheel. Publish to TestPyPI. This is the single most operationally painful thing in Python packaging; doing it once removes the fear.
