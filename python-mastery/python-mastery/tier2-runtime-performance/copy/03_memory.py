"""T2 w4 — object sizes, slots, interning, GC generations, finding and fixing a leak."""
import gc
import sys
import tracemalloc
import weakref
from dataclasses import dataclass

print("=== sizes (shallow!) ===")
for label, obj in [("int 1", 1), ("int 2**64", 2**64), ("'' ", ""), ("'abc'", "abc"), ("()", ()), ("[]", []),
                   ("{}", {}), ("set()", set()), ("object()", object()), ("1.0", 1.0), ("None", None)]:
    print(f"  {label:<10} {sys.getsizeof(obj):4} B")


class Plain:
    def __init__(self) -> None:
        self.a, self.b, self.c = 1, 2, 3


class Slotted:
    __slots__ = ("a", "b", "c")

    def __init__(self) -> None:
        self.a, self.b, self.c = 1, 2, 3


@dataclass(slots=True)
class DS:
    a: int
    b: int
    c: int


p, s = Plain(), Slotted()
print(f"  Plain: obj {sys.getsizeof(p)} + __dict__ {sys.getsizeof(p.__dict__)}  |  Slotted: {sys.getsizeof(s)}  |  DS: {sys.getsizeof(DS(1,2,3))}")
print("  dict keys shared across instances (PEP 412): first dict shows the split table cost")

print("=== interning and caches ===")
a, b = 256, 256
c, d = 257, 257
print("  small-int cache:", a is b, "| 257 is 257 in one line:", c is d, "(same code object constant)")
e = int("257"); f = int("257")
print("  257 computed twice:", e is f)
s1 = "hello_world"; s2 = "hello_world"
print("  identifier-like strings are interned:", s1 is s2, "| explicit:", sys.intern("a b") is sys.intern("a b"))
print("  immortal (3.12+): refcount of None:", sys.getrefcount(None))

print("=== refcounting vs cyclic GC ===")


class Node:
    def __init__(self) -> None:
        self.ref: Node | None = None


gc.collect()
n1, n2 = Node(), Node()
n1.ref, n2.ref = n2, n1                     # cycle
wr = weakref.ref(n1)
del n1, n2
print("  after del, cycle still alive (refcount can't free it):", wr() is not None)
print("  gc.collect() freed:", gc.collect(), "objects; alive now:", wr() is not None)
print("  thresholds:", gc.get_threshold(), "| stats gens:", [s["collections"] for s in gc.get_stats()])

print("=== finding a leak with tracemalloc ===")
_registry: list[object] = []


def leaky_handler(payload: bytes) -> None:
    class Callback:                          # closure captures payload; registry keeps Callback alive
        def __call__(self) -> int:
            return len(payload)
    _registry.append(Callback())


tracemalloc.start(10)
snap1 = tracemalloc.take_snapshot()
for _ in range(2000):
    leaky_handler(b"x" * 1000)
snap2 = tracemalloc.take_snapshot()
top = snap2.compare_to(snap1, "traceback")[0]
print(f"  +{top.size_diff / 1e6:.1f} MB from:")
for line in top.traceback.format()[-2:]:
    print("   ", line)
tracemalloc.stop()

print("=== fix: weak registry ===")
_weak: weakref.WeakSet[object] = weakref.WeakSet()


class Handler:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        _weak.add(self)


hs = [Handler(b"x") for _ in range(10)]
print("  registered:", len(_weak))
del hs
print("  after callers drop them:", len(_weak))

print("=== who references this object? ===")
target = object()
holder = {"k": target}
print("  referrers:", [type(r).__name__ for r in gc.get_referrers(target) if r is not globals()])
