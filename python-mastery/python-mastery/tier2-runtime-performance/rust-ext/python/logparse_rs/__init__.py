"""Typed façade over the native module."""

from __future__ import annotations

from logparse_rs._native import aggregate as _aggregate

__all__ = ["aggregate"]


def aggregate(path: str) -> dict[str, dict[str, float | int]]:
    """Parse ``path`` and aggregate per ``"status|endpoint"``."""
    result: dict[str, dict[str, float | int]] = _aggregate(path)
    return result
