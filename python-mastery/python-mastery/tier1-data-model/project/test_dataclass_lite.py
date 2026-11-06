import pickle
from typing import ClassVar

import pytest
from dataclasses import FrozenInstanceError

from dataclass_lite import asdict, field, fields, record, replace


@record
class P:
    x: int
    y: int = 0
    tags: list[str] = field(default_factory=list)
    counter: ClassVar[int] = 0


def test_init_repr_eq() -> None:
    p = P(1)
    assert (p.x, p.y, p.tags) == (1, 0, [])
    assert repr(p) == "P(x=1, y=0, tags=[])"
    assert P(1, 2) == P(1, 2) and P(1) != P(2)
    assert P(1).tags is not P(1).tags          # factory called per instance
    assert P.__match_args__ == ("x", "y", "tags")
    assert [f.name for f in fields(P)] == ["x", "y", "tags"]


def test_generated_source_is_real_function() -> None:
    assert P.__init__.__name__ == "__init__"
    assert P.__init__.__code__.co_varnames[:3] == ("self", "x", "y")


def test_mutable_default_rejected() -> None:
    with pytest.raises(ValueError, match="mutable"):
        @record
        class Bad:
            xs: list[int] = []


def test_ordering_of_defaults() -> None:
    with pytest.raises(TypeError, match="non-default"):
        @record
        class Bad:
            a: int = 1
            b: int  # type: ignore[misc]


def test_frozen_hash_slots() -> None:
    @record(frozen=True, slots=True)
    class V:
        a: int
        b: str = "x"

    v = V(1)
    with pytest.raises(FrozenInstanceError):
        v.a = 2  # type: ignore[misc]
    assert hash(v) == hash(V(1)) and {v, V(1)} == {v}
    assert not hasattr(v, "__dict__") and V.__slots__ == ("a", "b")
    with pytest.raises(AttributeError):
        v.zzz = 1  # type: ignore[attr-defined]


def test_inheritance_and_override() -> None:
    @record
    class Base:
        a: int
        b: int = 1

    @record
    class Child(Base):
        b: int = 2
        c: int = 3

    assert [f.name for f in fields(Child)] == ["a", "b", "c"]
    assert Child(0) == Child(0, 2, 3) and repr(Child(0)) == "Child(a=0, b=2, c=3)"


def test_repr_compare_flags() -> None:
    @record
    class S:
        a: int
        secret: str = field(default="", repr=False, compare=False)

    assert repr(S(1, "x")) == "S(a=1)" and S(1, "x") == S(1, "y")


def test_helpers_and_pickle() -> None:
    p = P(1, 2, ["t"])
    assert asdict(p) == {"x": 1, "y": 2, "tags": ["t"]}
    assert replace(p, y=9) == P(1, 9, ["t"])
    assert pickle.loads(pickle.dumps(p)) == p


def test_match() -> None:
    match P(3, 4):
        case P(x, y):
            assert (x, y) == (3, 4)
        case _:
            raise AssertionError
