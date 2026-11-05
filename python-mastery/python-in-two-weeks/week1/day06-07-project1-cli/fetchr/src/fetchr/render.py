"""Output: rich tables or JSON."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table

from fetchr.models import Issue, Repo

console = Console()


def _default(o: object) -> Any:
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"not serialisable: {type(o).__name__}")


def to_json(items: Iterable[Any]) -> str:
    rows = [
        dataclasses.asdict(i) if dataclasses.is_dataclass(i) and not isinstance(i, type) else i
        for i in items
    ]
    return json.dumps(rows, indent=2, default=_default)


def repo_table(repos: Iterable[Repo]) -> Table:
    t = Table(title="Repositories")
    for col in ("Repo", "Stars", "Forks", "Issues", "Lang", "Pushed"):
        t.add_column(col, justify="right" if col in {"Stars", "Forks", "Issues"} else "left")
    for r in repos:
        t.add_row(
            r.full_name,
            f"{r.stars:,}",
            f"{r.forks:,}",
            str(r.open_issues),
            r.language,
            r.pushed_at.date().isoformat(),
        )
    return t


def issue_table(issues: Iterable[Issue]) -> Table:
    t = Table(title="Issues")
    t.add_column("#", justify="right")
    t.add_column("Title", max_width=60)
    t.add_column("Author")
    t.add_column("Opened")
    for i in issues:
        t.add_row(str(i.number), i.title, i.author, i.created_at.date().isoformat())
    return t
