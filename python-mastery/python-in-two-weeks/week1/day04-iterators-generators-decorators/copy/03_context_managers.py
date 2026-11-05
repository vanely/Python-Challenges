"""Day 4 — context managers."""
import contextlib
import os
import time
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType


class Timer:
    """Class-based: __enter__ / __exit__."""

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed = time.perf_counter() - self.start
        print(f"took {self.elapsed * 1000:.2f} ms")
        # returning None/False = don't swallow exceptions; return True to swallow


with Timer() as t:
    sum(range(100_000))
print(t.elapsed > 0)


@contextlib.contextmanager
def cd(path: Path) -> Iterator[None]:
    """Generator-based: before yield = enter, after = exit."""
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:                            # runs even if the body raises
        os.chdir(prev)


with cd(Path("/tmp")):
    print(Path.cwd())
print(Path.cwd())


@contextlib.contextmanager
def opened(path: Path, mode: str = "r") -> Iterator[object]:
    f = path.open(mode)
    try:
        yield f
    finally:
        f.close()


# exceptions propagate through the manager
class Resource:
    def __enter__(self) -> "Resource":
        print("acquire")
        return self

    def __exit__(self, *exc: object) -> None:
        print("release (exc:", exc[0] is not None, ")")


try:
    with Resource():
        raise RuntimeError("boom")
except RuntimeError:
    print("caught outside")

# stdlib helpers
with contextlib.suppress(FileNotFoundError):
    Path("does-not-exist").unlink()      # silently ignored
print("suppressed")

with contextlib.ExitStack() as stack:    # manage N resources dynamically
    files = [stack.enter_context(Path(f"/tmp/_{i}.txt").open("w")) for i in range(3)]
    print(len(files), "files open")
print("all closed")
for i in range(3):
    Path(f"/tmp/_{i}.txt").unlink()

# multiple in one statement
with Timer(), contextlib.suppress(ZeroDivisionError):
    1 / 0
print("still here")
