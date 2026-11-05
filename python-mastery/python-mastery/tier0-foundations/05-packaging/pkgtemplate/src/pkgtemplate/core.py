"""Core functions."""

from __future__ import annotations

import re
import warnings

_NON_WORD = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, sep: str = "-") -> str:
    """Lowercase, replace non-alphanumerics with ``sep``, trim.

    >>> slugify("Hello, World!")
    'hello-world'
    """
    return _NON_WORD.sub(sep, text.lower()).strip(sep)


def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


def old_greet(name: str) -> str:
    """Return a greeting (deprecated alias for :func:`greet`; removed in 1.0)."""
    warnings.warn("old_greet() is deprecated; use greet()", DeprecationWarning, stacklevel=2)
    return greet(name)
