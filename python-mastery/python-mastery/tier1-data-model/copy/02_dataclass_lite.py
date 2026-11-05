"""T1 w2 — how dataclasses work under the hood (exec-generated methods), copy semantics, weakrefs."""
from __future__ import annotations

import copy
import dataclasses
import gc
import weakref
from dataclasses import dataclass, field, fields
from typing import Any


@dataclass(order=True, frozen=True, slots=True)
class Version:
    major: int
    minor: int = 0
    tags: tuple[str, ...] = field(default=(), compare=False, repr=False)


v = Version(1, 2, ("beta",))
print(v, v < Version(2), hash(v), Version.__match_args__)
print([f.name for f in fields(Version)])
print(dataclasses.asdict(v), dataclasses.replace(v, minor=9))

# Peek at what the decorator generated: it builds source text and exec()s it.
import inspect
print(inspect.getsource(dataclasses._init_fn)[:300].strip().splitlines()[0], "...")   # type: ignore[attr-defined]


@dataclass
class Node:
    name: str
    children: list[Node] = field(default_factory=list)   # never `= []`
    parent: Node | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        for c in self.children:
            c.parent = self


root = Node("root", [Node("a"), Node("b")])
print(root, root.children[0].parent is root)

# --- copy semantics ------------------------------------------------------------------------------
shallow = copy.copy(root)
deep = copy.deepcopy(root)
print(shallow.children is root.children, deep.children is root.children)   # True False
print(deep.children[0].parent is deep)                                     # cycles preserved by memo


class Resource:
    def __init__(self, handle: int) -> None:
        self.handle = handle

    def __deepcopy__(self, memo: dict[int, Any]) -> Resource:
        return self                          # opt out: handles shouldn't be duplicated


print(copy.deepcopy([Resource(1)])[0].handle)

# --- references and weakrefs --------------------------------------------------------------------------
class Big:
    pass


obj = Big()
r = weakref.ref(obj)
print(r() is obj)
cache: weakref.WeakValueDictionary[str, Big] = weakref.WeakValueDictionary()
cache["k"] = obj
del obj
gc.collect()
print(r(), "k" in cache)                     # None False — nothing kept it alive


class Temp:
    def __init__(self) -> None:
        weakref.finalize(self, print, "  finalizer ran")


t = Temp()
del t
