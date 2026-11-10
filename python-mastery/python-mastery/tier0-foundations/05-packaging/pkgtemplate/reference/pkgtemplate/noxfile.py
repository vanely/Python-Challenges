"""nox -l to list; nox -s tests-3.12; nox (runs default sessions)."""

import nox

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["lint", "typecheck", "tests"]
PYTHONS = ["3.12", "3.13"]


@nox.session(python=PYTHONS)
def tests(session: nox.Session) -> None:
    session.install("-e", ".[cli]", "pytest", "pytest-cov")
    session.run("pytest", *session.posargs)


@nox.session
def lint(session: nox.Session) -> None:
    session.install("ruff")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session
def typecheck(session: nox.Session) -> None:
    session.install("-e", ".[cli]", "mypy", "pytest")
    session.run("mypy")


@nox.session
def build(session: nox.Session) -> None:
    session.install("uv")
    session.run("uv", "build")
    session.run("uv", "run", "--with", "twine", "twine", "check", "dist/*")
