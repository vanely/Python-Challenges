"""Day 5 — the pytest idioms you'll actually use. Run: pytest test_examples.py -v"""
from pathlib import Path

import pytest


# --- fixtures: DI by argument name ---------------------------------------------
@pytest.fixture
def sample_users() -> list[dict[str, object]]:
    return [{"id": 1, "name": "ada"}, {"id": 2, "name": "grace"}]


def test_fixture_injection(sample_users: list[dict[str, object]]) -> None:
    assert len(sample_users) == 2


# --- built-in fixtures ------------------------------------------------------------
def test_tmp_path(tmp_path: Path) -> None:      # unique temp dir per test
    f = tmp_path / "data.txt"
    f.write_text("hello")
    assert f.read_text() == "hello"


def test_capsys(capsys: pytest.CaptureFixture[str]) -> None:
    print("out!")
    assert capsys.readouterr().out == "out!\n"


def test_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    monkeypatch.setenv("APP_ENV", "test")
    assert os.environ["APP_ENV"] == "test"
    monkeypatch.setattr(os.path, "sep", "|")
    assert os.path.sep == "|"                   # restored after the test


# --- parametrize: table-driven tests ---------------------------------------------
@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(1, 2, 3), (0, 0, 0), (-1, 1, 0)],
    ids=["positive", "zeros", "negatives"],
)
def test_add(a: int, b: int, expected: int) -> None:
    assert a + b == expected


# --- exceptions and floats ----------------------------------------------------------
def test_raises() -> None:
    with pytest.raises(ValueError, match="invalid literal"):
        int("x")


def test_approx() -> None:
    total = 0.1 + 0.2
    assert total == pytest.approx(0.3)


# --- fixture with teardown (yield) ---------------------------------------------------
@pytest.fixture
def resource() -> "Iterator[str]":
    print("setup")
    yield "handle"
    print("teardown")


from collections.abc import Iterator  # noqa: E402


def test_uses_resource(resource: str) -> None:
    assert resource == "handle"


# --- marks --------------------------------------------------------------------------
@pytest.mark.skip(reason="demo of skip")
def test_skipped() -> None:
    raise AssertionError


@pytest.mark.xfail(reason="known bug")
def test_expected_failure() -> None:
    assert int("1") == 2
