"""Step 1: models. Spec: steps/01-scaffold-and-models.md."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from fetchr.models import Issue, IssueState, Repo


def test_repo_from_full_payload(repo_payload: dict[str, Any]) -> None:
    r = Repo.from_api(repo_payload)  # type: ignore[arg-type]
    assert r.full_name == "encode/httpx"
    assert (r.stars, r.forks, r.open_issues) == (13000, 800, 50)
    assert r.language == "Python"
    assert r.url == "https://github.com/encode/httpx"
    assert r.pushed_at == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_timestamps_are_timezone_aware(repo_payload: dict[str, Any]) -> None:
    r = Repo.from_api(repo_payload)  # type: ignore[arg-type]
    assert r.pushed_at is not None
    assert r.pushed_at.utcoffset() == timedelta(0), "parse the Z as UTC, don't drop it"


def test_repo_defaults_when_keys_missing_or_null() -> None:
    r = Repo.from_api({"full_name": "a/b", "description": None, "language": None})
    assert r.description == ""
    assert r.language == "—"
    assert (r.stars, r.forks, r.open_issues) == (0, 0, 0)
    assert r.url == ""
    assert r.pushed_at is None, "a missing timestamp is None, not a fake date"


def test_issue_from_api() -> None:
    i = Issue.from_api(
        {
            "number": 7,
            "title": "Bug",
            "state": "closed",
            "created_at": "2026-05-01T00:00:00Z",
            "html_url": "u",
            "user": {"login": "ada"},
        }
    )
    assert (i.number, i.title, i.state, i.author, i.url) == (7, "Bug", "closed", "ada", "u")
    assert i.created_at == datetime(2026, 5, 1, tzinfo=UTC)


def test_issue_author_when_user_missing_or_null() -> None:
    assert Issue.from_api({"number": 1, "title": "t"}).author == "?"
    assert Issue.from_api({"number": 1, "title": "t", "user": None}).author == "?"
    assert Issue.from_api({"number": 1, "title": "t"}).created_at is None


def test_models_are_frozen_and_slotted(repo_payload: dict[str, Any]) -> None:
    r = Repo.from_api(repo_payload)  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.stars = 1  # type: ignore[misc]
    assert not hasattr(r, "__dict__"), "use @dataclass(frozen=True, slots=True)"
    assert dataclasses.is_dataclass(Issue)


def test_models_compare_by_value(repo_payload: dict[str, Any]) -> None:
    a = Repo.from_api(repo_payload)  # type: ignore[arg-type]
    b = Repo.from_api(dict(repo_payload))  # type: ignore[arg-type]
    assert a == b and a is not b
    assert hash(a) == hash(b), "frozen dataclasses are hashable"


def test_issue_state_is_a_str_enum() -> None:
    assert IssueState("open") is IssueState.OPEN
    assert {s.value for s in IssueState} == {"open", "closed", "all"}
    assert IssueState.CLOSED == "closed" and str(IssueState.ALL) == "all"
