"""Day 4 — decorators, typed properly."""
import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


# --- 1. plain decorator ----------------------------------------------------------
def log_calls(fn: Callable[P, R]) -> Callable[P, R]:
    @functools.wraps(fn)                          # keep __name__/__doc__/signature
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        print(f"-> {fn.__name__}{args}{kwargs or ''}")
        result = fn(*args, **kwargs)
        print(f"<- {result!r}")
        return result

    return wrapper


@log_calls
def add(a: int, b: int) -> int:
    """Add two ints."""
    return a + b


add(2, 3)
print(add.__name__, add.__doc__)                   # preserved thanks to wraps
# without @log_calls, `add = log_calls(add)` is the same thing


# --- 2. decorator with arguments -------------------------------------------------
def retry(times: int, delay: float = 0.0) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:  # noqa: BLE001 — narrow this in real code
                    last = e
                    print(f"attempt {attempt} failed: {e}")
                    time.sleep(delay)
            assert last is not None
            raise last

        return wrapper

    return decorator


calls = 0


@retry(times=3)
def flaky() -> str:
    global calls
    calls += 1
    if calls < 3:
        raise ConnectionError("nope")
    return "ok"


print(flaky())


# --- 3. class-based decorator (stateful) -------------------------------------------
class CountCalls[**Q, S]:                          # 3.12 generic-class syntax
    def __init__(self, fn: Callable[Q, S]) -> None:
        functools.update_wrapper(self, fn)
        self.fn = fn
        self.n = 0

    def __call__(self, *args: Q.args, **kwargs: Q.kwargs) -> S:
        self.n += 1
        return self.fn(*args, **kwargs)


@CountCalls
def ping() -> None:
    pass


ping(); ping()
print(ping.n)


# --- 4. stacking: bottom applies first -------------------------------------------
@log_calls
@functools.cache                                  # memoize
def slow_square(n: int) -> int:
    time.sleep(0.01)
    return n * n


slow_square(4)
slow_square(4)                                     # cached; log_calls still fires


# --- 5. functools.partial and singledispatch ----------------------------------------
def power(base: float, exp: float) -> float:
    return float(base**exp)


square = functools.partial(power, exp=2)
print(square(5.0))


@functools.singledispatch
def render(x: object) -> str:
    return f"<{x!r}>"


@render.register
def _(x: int) -> str:
    return f"int:{x}"


@render.register
def _(x: list) -> str:  # type: ignore[type-arg]
    return "[" + ", ".join(render(i) for i in x) + "]"


print(render(1), render("s"), render([1, "a"]))


# --- 6. decorators are everywhere in the ecosystem -----------------------------------
# @property, @staticmethod, @classmethod, @dataclass, @pytest.fixture,
# @app.get("/"), @click.command(), @contextlib.contextmanager, @overload
