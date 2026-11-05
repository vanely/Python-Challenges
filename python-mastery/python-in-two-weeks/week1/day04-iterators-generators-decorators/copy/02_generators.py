"""Day 4 — generators and itertools."""
import itertools as it
from collections.abc import Iterable, Iterator


def countdown(n: int) -> Iterator[int]:
    print("  (generator started)")
    while n > 0:
        yield n
        n -= 1
    print("  (generator finished)")


g = countdown(3)                        # nothing runs yet
print(type(g).__name__)
print(next(g))                          # runs to first yield
print(list(g))                          # rest


def fib() -> Iterator[int]:
    """Infinite generator — fine, because it's lazy."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


print(list(it.islice(fib(), 10)))
print(next(x for x in fib() if x > 1000))


# a pipeline: each stage is lazy; nothing is materialized until consumed
def read_lines(text: str) -> Iterator[str]:
    yield from text.splitlines()        # yield from == yield*


def strip_comments(lines: Iterable[str]) -> Iterator[str]:
    for line in lines:
        if not line.startswith("#"):
            yield line


def parse_ints(lines: Iterable[str]) -> Iterator[int]:
    for line in lines:
        if line.strip():
            yield int(line)


src = "# header\n1\n2\n\n# mid\n3\n"
total = sum(parse_ints(strip_comments(read_lines(src))))
print(total)


# generator with return value and send (rare; know it exists)
def accumulator() -> "Generator[int, int, str]":
    total = 0
    while True:
        received = yield total
        if received < 0:
            return "done"
        total += received


from collections.abc import Generator  # noqa: E402

acc = accumulator()
next(acc)                               # prime it
print(acc.send(5), acc.send(10))
try:
    acc.send(-1)
except StopIteration as e:
    print("returned:", e.value)


# itertools you'll use constantly
print(list(it.chain([1, 2], (3, 4))))
print(list(it.batched(range(7), 3)))                     # 3.12
print(list(it.pairwise("abcd")))
print(list(it.takewhile(lambda x: x < 4, range(10))))
print(list(it.accumulate([1, 2, 3, 4])))
print([(k, list(grp)) for k, grp in it.groupby("aabbbc")])   # input must be sorted by key
print(list(it.product("ab", [1, 2])))
print(list(it.combinations("abc", 2)))
print(list(it.zip_longest("ab", "xyz", fillvalue="-")))
counter = it.count(10, 5)
print(next(counter), next(counter))
