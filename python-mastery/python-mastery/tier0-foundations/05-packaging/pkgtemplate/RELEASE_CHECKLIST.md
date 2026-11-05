# Release checklist

1. `CHANGELOG.md`: move Unreleased → `[X.Y.Z] - YYYY-MM-DD`.
2. `nox` green locally; CI green on main.
3. `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z` — the tag *is* the version.
4. Watch the Release workflow: build → TestPyPI → PyPI (approve the environment if gated).
5. Verify: `python -m venv /tmp/v && /tmp/v/bin/pip install pkgtemplate==X.Y.Z && /tmp/v/bin/python -c "import pkgtemplate; print(pkgtemplate.__version__)"`.
6. Open the next `[Unreleased]` section.

First time only: on (test.)pypi.org → your project → Publishing → add a Trusted Publisher with owner/repo/workflow `release.yml`/environment name.
