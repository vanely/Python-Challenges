"""Domain models. Frozen dataclasses built from TypedDict-shaped API payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypedDict

IssueState = Literal["open", "closed", "all"]


class RepoPayload(TypedDict, total=False):
    """Subset of GET /repos/{owner}/{repo}. total=False: keys may be missing."""

    full_name: str
    description: str | None
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    language: str | None
    html_url: str
    pushed_at: str


class IssuePayload(TypedDict, total=False):
    number: int
    title: str
    state: str
    created_at: str
    html_url: str
    user: dict[str, object]
    pull_request: dict[str, object]  # present only when the "issue" is a PR


@dataclass(frozen=True, slots=True)
class Repo:
    full_name: str
    description: str
    stars: int
    forks: int
    open_issues: int
    language: str
    url: str
    pushed_at: datetime

    @classmethod
    def from_api(cls, data: RepoPayload) -> Repo:
        return cls(
            full_name=data["full_name"],
            description=data.get("description") or "",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            language=data.get("language") or "—",
            url=data.get("html_url", ""),
            pushed_at=_parse_dt(data.get("pushed_at")),
        )


@dataclass(frozen=True, slots=True)
class Issue:
    number: int
    title: str
    state: str
    author: str
    created_at: datetime
    url: str

    @classmethod
    def from_api(cls, data: IssuePayload) -> Issue:
        user = data.get("user") or {}
        return cls(
            number=data["number"],
            title=data["title"],
            state=data.get("state", "open"),
            author=str(user.get("login", "?")),
            created_at=_parse_dt(data.get("created_at")),
            url=data.get("html_url", ""),
        )


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.min
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
