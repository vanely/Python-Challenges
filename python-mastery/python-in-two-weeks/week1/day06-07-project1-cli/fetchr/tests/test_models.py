from typing import cast

from fetchr.models import Issue, IssuePayload, Repo, RepoPayload


def test_repo_from_api(repo_payload: dict[str, object]) -> None:
    r = Repo.from_api(cast(RepoPayload, repo_payload))
    assert r.full_name == "encode/httpx"
    assert r.stars == 13000
    assert r.pushed_at.year == 2026


def test_repo_defaults_when_missing() -> None:
    r = Repo.from_api({"full_name": "a/b"})
    assert r.language == "—"
    assert r.description == ""


def test_issue_from_api() -> None:
    payload: IssuePayload = {
        "number": 7,
        "title": "Bug",
        "state": "open",
        "created_at": "2026-05-01T00:00:00Z",
        "html_url": "u",
        "user": {"login": "ada"},
    }
    i = Issue.from_api(payload)
    assert i.author == "ada" and i.number == 7
