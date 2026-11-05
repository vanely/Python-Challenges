"""Skeleton for your vector.py. Uncomment as you implement. Run: pytest test_vector.py"""
import math
import pickle

import pytest

from vector import Vector  # type: ignore[import-not-found]


def test_construct_repr_iter() -> None:
    v = Vector([3, 4])
    assert repr(v) == "Vector([3.0, 4.0])" and list(v) == [3.0, 4.0] and len(v) == 2
    assert repr(Vector(range(10))).endswith("...])")     # reprlib-style truncation


def test_abs_bool_eq_hash() -> None:
    assert abs(Vector([3, 4])) == 5 and bool(Vector([0, 0])) is False
    assert Vector([1, 2]) == Vector([1, 2]) and Vector([1, 2]) != Vector([1, 2, 3])
    assert Vector([1, 2]) != (1, 2)                       # no silent tuple equality (decide!)
    assert hash(Vector([1, 2])) == hash(Vector([1, 2]))


def test_slicing_returns_vector() -> None:
    v = Vector(range(7))
    assert v[-1] == 6.0 and isinstance(v[1:4], Vector) and list(v[1:4]) == [1, 2, 3]
    with pytest.raises(TypeError):
        v[1, 2]  # type: ignore[index]


def test_getattr_and_setattr_guard() -> None:
    v = Vector([1, 2, 3, 4])
    assert (v.x, v.y, v.z, v.t) == (1, 2, 3, 4)
    with pytest.raises(AttributeError):
        v.x = 9  # type: ignore[misc]
    with pytest.raises(AttributeError):
        v.spam  # noqa: B018


def test_operators() -> None:
    v = Vector([1, 2])
    assert v + Vector([1, 1]) == Vector([2, 3]) and v + (1, 1) == Vector([2, 3]) and (1, 1) + v == Vector([2, 3])
    assert v * 2 == Vector([2, 4]) and 2 * v == Vector([2, 4]) and -v == Vector([-1, -2]) and +v == v
    assert v @ Vector([3, 4]) == 11
    with pytest.raises(TypeError):
        v * "a"  # type: ignore[operator]
    assert v.__add__("x") is NotImplemented


def test_format() -> None:
    assert format(Vector([1, 1]), ".2f") == "(1.00, 1.00)"
    assert format(Vector([1, 1]), ".2fh") == "<1.41, 0.79>"      # hyperspherical
    assert math.isclose(float(format(Vector([1, 0]), ".1fh").split(",")[1].rstrip(">")), 0.0)


def test_bytes_roundtrip_and_pickle() -> None:
    v = Vector([1.5, -2])
    assert Vector.frombytes(bytes(v)) == v
    assert pickle.loads(pickle.dumps(v)) == v
