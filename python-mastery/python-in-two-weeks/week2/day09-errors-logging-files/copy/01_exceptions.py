"""Day 9 — exceptions the Python way."""
from __future__ import annotations

import json
from pathlib import Path


# --- a hierarchy --------------------------------------------------------------------
class AppError(Exception):
    """Base for everything this app raises."""


class ConfigError(AppError):
    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


class ValidationError(AppError):
    pass


# --- EAFP + chaining + else/finally ---------------------------------------------------
def load_config(path: Path) -> dict[str, object]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise ConfigError(path, "missing") from e            # keep the cause
    except PermissionError as e:
        raise ConfigError(path, "not readable") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ConfigError(path, f"invalid JSON at line {e.lineno}") from e
    else:                                                    # only on success
        if not isinstance(data, dict):
            raise ValidationError("config must be an object")
        return data
    finally:
        print(f"  (attempted {path.name})")


tmp = Path("_cfg.json")
for content in ['{"a": 1}', "{bad", None]:
    if content is None:
        tmp.unlink(missing_ok=True)
    else:
        tmp.write_text(content)
    try:
        print("loaded", load_config(tmp))
    except ConfigError as e:
        print("config problem:", e, "| cause:", type(e.__cause__).__name__)
    except AppError as e:                                     # base class catches the rest
        print("app error:", e)

# --- EAFP vs LBYL ------------------------------------------------------------------------
d = {"k": 1}
try:                                                          # EAFP (preferred)
    v = d["missing"]
except KeyError:
    v = 0
print(v)

# --- narrow catches; re-raise -----------------------------------------------------------------
def parse_port(s: str) -> int:
    try:
        port = int(s)
    except ValueError:
        raise ValidationError(f"port must be an int, got {s!r}") from None   # hide cause
    if not 0 < port < 65536:
        raise ValidationError(f"port out of range: {port}")
    return port


for s in ("8080", "x", "70000"):
    try:
        print(parse_port(s))
    except ValidationError as e:
        print("invalid:", e)

# --- exception groups (3.11) -------------------------------------------------------------------
try:
    raise ExceptionGroup("multiple", [ValueError("a"), TypeError("b")])
except* ValueError as eg:
    print("value errors:", [str(e) for e in eg.exceptions])
except* TypeError as eg:
    print("type errors:", [str(e) for e in eg.exceptions])

# --- custom __str__ and attributes ------------------------------------------------------------
class HttpError(AppError):
    def __init__(self, status: int, url: str) -> None:
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.url = url

    @property
    def retryable(self) -> bool:
        return self.status >= 500


try:
    raise HttpError(503, "https://x")
except HttpError as e:
    print(e, e.retryable)
