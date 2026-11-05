import json
from typing import Any

import pytest
from typer.testing import CliRunner

from fetchr import cli
from fetchr.models import Repo

runner = CliRunner()


class FakeClient:
    def __init__(self, repos: dict[str, Repo]) -> None:
        self._repos = repos

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *a: object) -> None:
        pass

    def repo(self, owner: str, name: str) -> Repo:
        return self._repos[f"{owner}/{name}"]


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, repo_payload: dict[str, Any]) -> None:
    r = Repo.from_api(repo_payload)  # type: ignore[arg-type]
    monkeypatch.setattr(cli, "_client", lambda: FakeClient({"encode/httpx": r}))


def test_repo_json(fake: None) -> None:
    result = runner.invoke(cli.app, ["repo", "encode/httpx", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data[0]["full_name"] == "encode/httpx"


def test_repo_table(fake: None) -> None:
    result = runner.invoke(cli.app, ["repo", "encode/httpx"])
    assert result.exit_code == 0
    assert "13,000" in result.output


def test_bad_slug(fake: None) -> None:
    result = runner.invoke(cli.app, ["repo", "nope"])
    assert result.exit_code != 0
