"""Day 2 — comprehensions and builtins that replace map/filter/reduce."""
import re
from functools import reduce
from operator import mul

nums = list(range(1, 11))

evens = [n for n in nums if n % 2 == 0]
squares = {n: n * n for n in nums}
roots = {n // 2 for n in nums}                  # set: duplicates collapse
print(evens, squares[7], sorted(roots))

# generator expression: lazy, single-pass, memory-cheap
total = sum(n * n for n in nums)
first_big = next(n for n in nums if n > 6)
print(total, first_big)

# nested — reads like nested for-loops, outer first
matrix = [[1, 2, 3], [4, 5, 6]]
flat = [cell for row in matrix for cell in row]
transposed = [[row[i] for row in matrix] for i in range(3)]
print(flat, transposed)

# conditional expression inside a comprehension
labels = ["even" if n % 2 == 0 else "odd" for n in nums]
print(labels[:4])

# walrus (3.8+): bind inside an expression
lines = ["id=1", "junk", "id=22"]
ids = [int(m.group(1)) for line in lines if (m := re.match(r"id=(\d+)", line))]
print(ids)

# builtins you'll reach for constantly
print(any(n > 9 for n in nums), all(n > 0 for n in nums))
print(min(nums), max(nums, key=lambda n: -n))
print(list(zip(*matrix)))                         # transpose via unpacking
print(list(enumerate("ab")))
print(sorted(["b", "A", "c"], key=str.casefold))
print(list(reversed(nums))[:3])
print(reduce(mul, nums))                          # factorial — rare; usually a loop is clearer

# dict from two lists, and inverting a dict
keys = ["a", "b"]
vals = [1, 2]
d = dict(zip(keys, vals))
inv = {v: k for k, v in d.items()}
print(d, inv)

# when NOT to use a comprehension: side effects, or >2 clauses
results = []
for n in nums:
    if n % 3 == 0:
        print("processing", n)                     # side effect -> use a loop
        results.append(n)
print(results)
