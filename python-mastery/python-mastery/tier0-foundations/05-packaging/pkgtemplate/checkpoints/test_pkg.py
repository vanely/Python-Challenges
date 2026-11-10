import pytest

from pkgtemplate import __version__, greet, slugify
from pkgtemplate.core import old_greet


def test_version_present() -> None:
    assert isinstance(__version__, str)


@pytest.mark.parametrize(
    ("raw", "out"), [("Hello, World!", "hello-world"), ("  a  b ", "a-b"), ("x", "x")]
)
def test_slugify(raw: str, out: str) -> None:
    assert slugify(raw) == out


def test_greet() -> None:
    assert greet("ada") == "Hello, ada!"


def test_old_greet_warns() -> None:
    with pytest.deprecated_call():
        assert old_greet("x") == "Hello, x!"
