"""Day 4 — the iterator protocol, by hand."""
from collections.abc import Iterator


class Countdown:
    """An iterable that returns a fresh iterator each time."""

    def __init__(self, start: int) -> None:
        self.start = start

    def __iter__(self) -> Iterator[int]:
        return CountdownIterator(self.start)


class CountdownIterator:
    def __init__(self, n: int) -> None:
        self.n = n

    def __iter__(self) -> "CountdownIterator":
        return self                     # iterators are their own iterables

    def __next__(self) -> int:
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n + 1


cd = Countdown(3)
print(list(cd), list(cd))               # reusable: [3,2,1] [3,2,1]

it = iter(cd)
print(next(it), next(it), next(it))
try:
    next(it)
except StopIteration:
    print("exhausted")
print(next(it, "default"))              # sentinel instead of exception

# what `for` does:
it = iter([10, 20])
while True:
    try:
        x = next(it)
    except StopIteration:
        break
    print(x)

# single-pass iterators — a classic bug
squares = map(lambda n: n * n, [1, 2, 3])
print(list(squares))                    # [1, 4, 9]
print(list(squares))                    # []  <-- consumed

# files are iterators of lines
from pathlib import Path
p = Path("_tmp.txt")
p.write_text("a\nb\nc\n")
with p.open() as f:
    for line in f:
        print(line.rstrip())
p.unlink()

# dicts iterate over keys; use .items() for pairs
for k in {"x": 1}:
    print(k)

# zip stops at the shortest; strict=True (3.10) raises instead
print(list(zip([1, 2, 3], "ab")))
try:
    list(zip([1, 2, 3], "ab", strict=True))
except ValueError as e:
    print("strict zip:", e)
