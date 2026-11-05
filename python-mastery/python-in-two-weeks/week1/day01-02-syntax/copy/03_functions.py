"""Day 2 — functions, arguments, scope."""
from typing import Callable


def greet(name: str, greeting: str = "Hello", *, shout: bool = False) -> str:
    """Everything after `*` is keyword-only."""
    msg = f"{greeting}, {name}!"
    return msg.upper() if shout else msg


print(greet("Ada"))
print(greet("Ada", "Hi"))
print(greet("Ada", shout=True))
# greet("Ada", "Hi", True)   # TypeError: shout is keyword-only


def total(*nums: float, start: float = 0.0) -> float:
    """*nums collects positional args into a tuple."""
    return start + sum(nums)


print(total(1, 2, 3), total(1, 2, start=10))


def build_query(**filters: str) -> str:
    """**filters collects keyword args into a dict."""
    return " AND ".join(f"{k}={v!r}" for k, v in filters.items())


print(build_query(status="active", role="admin"))

args = (1, 2)
kwargs = {"start": 100.0}
print(total(*args, **kwargs))          # unpacking into a call


# --- the mutable default bug ----------------------------------------------
def bad_append(item: int, bucket: list[int] = []) -> list[int]:  # noqa: B006
    bucket.append(item)
    return bucket


print(bad_append(1), bad_append(2))    # [1, 2] [1, 2]  -- shared list!


def good_append(item: int, bucket: list[int] | None = None) -> list[int]:
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket


print(good_append(1), good_append(2))  # [1] [2]


# --- multiple return values are a tuple ------------------------------------
def min_max(values: list[int]) -> tuple[int, int]:
    return min(values), max(values)


lo, hi = min_max([4, 9, 1])
print(lo, hi)


# --- functions are values ---------------------------------------------------
def apply_twice(fn: Callable[[int], int], x: int) -> int:
    return fn(fn(x))


def double(v: int) -> int:
    return v * 2


print(apply_twice(double, 3))
print(apply_twice(lambda v: v + 1, 3))
print(list(map(str.upper, ["a", "b"])))   # map still exists; comprehensions preferred


# --- scope: LEGB (Local, Enclosing, Global, Builtin) ------------------------
counter = 0


def increment() -> None:
    global counter        # needed to rebind a module-level name
    counter += 1


def make_counter() -> Callable[[], int]:
    n = 0

    def tick() -> int:
        nonlocal n        # needed to rebind an enclosing-scope name
        n += 1
        return n

    return tick


increment()
tick = make_counter()
print(counter, tick(), tick())


# --- docstrings + annotations are introspectable ----------------------------
print(greet.__doc__)
print(greet.__annotations__)
