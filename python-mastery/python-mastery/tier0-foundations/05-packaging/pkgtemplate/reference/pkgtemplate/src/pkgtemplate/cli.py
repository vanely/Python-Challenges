"""CLI entry point (requires the ``cli`` extra)."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Kept importable without typer so ``import pkgtemplate`` never fails."""
    try:
        import typer
    except ImportError:
        print("install the cli extra: pip install 'pkgtemplate[cli]'", file=sys.stderr)
        return 2

    from pkgtemplate import __version__, greet

    app = typer.Typer(no_args_is_help=True)

    @app.command()
    def hello(name: str = "world") -> None:
        """Say hello."""
        print(greet(name))

    @app.command()
    def version() -> None:
        """Print the version."""
        print(__version__)

    app(args=argv)
    return 0
