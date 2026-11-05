"""Skeleton for config.py."""
import json
from typing import Literal

import pytest

from config import Config, ConfigError, Section  # type: ignore[import-not-found]


class Db(Section, name="db"):
    host: str
    port: int = 5432
    mode: Literal["ro", "rw"] = "rw"


class App(Section, name="app"):
    debug: bool = False
    workers: int = 1


RAW = {"db": {"host": "x", "port": 1}, "app": {"debug": True}}


def test_attribute_access_and_dir() -> None:
    cfg = Config.load(RAW)
    assert cfg.db.host == "x" and cfg.db.port == 1 and cfg.app.debug is True and cfg.app.workers == 1
    assert "db" in dir(cfg) and "host" in dir(cfg.db)
    assert repr(cfg.db).startswith("Db(")


def test_frozen() -> None:
    cfg = Config.load(RAW)
    with pytest.raises(AttributeError):
        cfg.db.port = 2  # type: ignore[misc]
    with pytest.raises(AttributeError):
        cfg.newsection = 1  # type: ignore[attr-defined]
    assert not hasattr(cfg.db, "__dict__")     # slots


def test_validation_collects_all_errors() -> None:
    bad = {"db": {"host": 1, "port": "x", "mode": "zz", "extra": 1}, "app": {}}
    with pytest.raises(ConfigError) as ei:
        Config.load(bad)
    msg = str(ei.value)
    for path in ("db.host", "db.port", "db.mode", "db.extra"):
        assert path in msg


def test_missing_section_and_key() -> None:
    with pytest.raises(ConfigError, match="db.host"):
        Config.load({"db": {}, "app": {}})


def test_env_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_DB__PORT", "9")
    monkeypatch.setenv("APP_APP__DEBUG", "false")
    cfg = Config.load(RAW).from_env(prefix="APP_")
    assert cfg.db.port == 9 and cfg.app.debug is False


def test_getattr_does_not_mask_property_errors() -> None:
    class Weird(Section, name="weird"):
        a: int = 1

        @property
        def boom(self) -> int:
            raise AttributeError("inner failure")

    cfg = Config.load({**RAW, "weird": {}})
    with pytest.raises(AttributeError, match="inner failure"):
        cfg.weird.boom  # noqa: B018


def test_roundtrip_json() -> None:
    cfg = Config.load(RAW)
    assert json.loads(cfg.to_json())["db"]["port"] == 1
