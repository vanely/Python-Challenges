# Day 1–2: Syntax, mapped from TypeScript

## Objectives
- Read and write core Python syntax without looking things up
- Replace `.map/.filter/.reduce` reflexes with comprehensions and builtins
- Understand truthiness, `None`, slicing, unpacking, `*args/**kwargs`

## Readings

| Source | Where | Read |
|---|---|---|
| Official tutorial ch. 3–5 | https://docs.python.org/3/tutorial/introduction.html, controlflow.html, datastructures.html | All. ~1.5 hr |
| `collections` module | https://docs.python.org/3/library/collections.html | `Counter`, `defaultdict`, `namedtuple`, `deque` sections only |
| Built-in functions | https://docs.python.org/3/library/functions.html | Skim; know `enumerate`, `zip`, `sorted`, `any`, `all`, `sum`, `min/max` with `key=` |
| *Fluent Python* ch. 2 "An Array of Sequences" | Book | Sections on list comprehensions, tuples as records, slicing |
| Real Python | "Python's Truthiness"; "When to Use a List Comprehension in Python" | Both short |

## Reading summaries — the parts that matter

### Blocks and statements
- Indentation *is* the block. 4 spaces. No braces, no semicolons. A colon opens a block.
- `if / elif / else`, `for x in iterable`, `while`. No `do-while`, no C-style `for(;;)`. Iterate with `range(n)`.
- `pass` is a no-op placeholder. `...` (Ellipsis) also works and is common in stubs.
- No `switch` until 3.10's `match` (structural pattern matching — much more powerful than switch; skim it, don't dwell).

### Variables and types
- No declarations. `x = 1`. Rebinding is fine. There's no `const`; convention is `UPPER_CASE` for constants and `Final` from `typing` for the checker.
- Everything is an object; `type(x)` and `isinstance(x, T)`.
- `int` is arbitrary precision. `/` is always float division; `//` is floor division. `**` is power.
- Strings: immutable, `'` and `"` are identical, `"""` for multi-line. f-strings: `f"{name!r} has {len(items)} items, {price:.2f}"`.

### Truthiness — different from JS
Falsy: `False`, `None`, `0`, `0.0`, `""`, `[]`, `{}`, `()`, `set()`. **Empty containers are falsy** — so `if items:` means "if non-empty." `==` is value equality with no string↔number coercion, but `bool` is an `int` subclass: `True == 1` and `0 == False`. `is` checks identity; use it for `None` and sentinel objects. For booleans, just write `if flag:`.

### Sequences and slicing
- `list` (mutable array), `tuple` (immutable, used for fixed-shape records), `str`, `range`.
- `seq[start:stop:step]`, negative indices from the end. `seq[::-1]` reverses. Slices return copies.
- Tuple unpacking: `a, b = b, a`; `first, *rest = items`; `for i, x in enumerate(items)`.

### Comprehensions — your new `map/filter`
```python
squares = [x * x for x in nums if x % 2 == 0]          # list
lookup  = {u.id: u for u in users}                       # dict
seen    = {tag.lower() for tag in tags}                  # set
total   = sum(x.price for x in cart)                     # generator, lazy
```
Nested comprehensions read left-to-right like nested loops. If it needs more than two clauses, write a loop.

### Functions
- `def f(a, b=2, *args, key=None, **kwargs) -> int:`
- Keyword arguments are first-class: `f(1, key="x")`. `*` alone forces keyword-only params after it; `/` forces positional-only before it.
- **Mutable default args are evaluated once.** Never `def f(items=[])`. Use `None` and assign inside.
- `lambda x: x * 2` — single expression only. Prefer `def` for anything named.
- Functions return `None` implicitly. Multiple returns are a tuple: `return lo, hi`.

### `collections`
- `Counter(words).most_common(3)` — histogram.
- `defaultdict(list)` — dict with auto-created default values; kills the `if key not in d: d[key] = []` pattern.
- `namedtuple` is old; prefer `dataclass` (Day 3).
- `deque` for O(1) appends/pops at both ends.

### Style basics (PEP 8)
`snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` constants, `_private` by convention (no enforcement), 88-col lines if using `ruff format`/black.

## TS → Python cheat sheet

| TypeScript | Python |
|---|---|
| `const xs = [1,2,3]` | `xs = [1, 2, 3]` |
| `xs.map(f)` | `[f(x) for x in xs]` |
| `xs.filter(p)` | `[x for x in xs if p(x)]` |
| `xs.reduce((a,b)=>a+b, 0)` | `sum(xs)` / `functools.reduce` |
| `xs.length` | `len(xs)` |
| `xs.includes(v)` | `v in xs` |
| `xs.push(v)` / `xs.pop()` | `xs.append(v)` / `xs.pop()` |
| `xs.slice(1, 3)` | `xs[1:3]` |
| `[...a, ...b]` | `[*a, *b]` or `a + b` |
| `{...a, ...b}` | `{**a, **b}` or `a \| b` |
| `Object.entries(o)` | `d.items()` |
| `o?.k ?? dflt` | `o.get("k", dflt)` (only when the key is missing). For null-coalescing: `v if (v := o.get("k")) is not None else dflt`. If `o` may be `None`: `(o or {}).get("k", dflt)` |
| `null` / `undefined` | `None` |
| `x === null` | `x is None` |
| `` `${a} b` `` | `f"{a} b"` |
| `(x) => x*2` | `lambda x: x * 2` |
| `for (const [i,x] of xs.entries())` | `for i, x in enumerate(xs):` |
| `try/catch/finally` | `try/except/finally` (+ `else`) |
| `throw new Error()` | `raise ValueError("msg")` |
| `console.log` | `print` |
| `typeof x` | `type(x)` / `isinstance(x, T)` |
| `x!` | not needed; `assert x is not None` for the checker |

## Copy (type these out, then run them)
`copy/01_basics.py` → `copy/02_collections.py` → `copy/03_functions.py` → `copy/04_comprehensions.py`

## Exercises
`copy/exercises.py` — 15 functions with docstrings and a stub body. Fill them in; `pytest copy/test_exercises.py` checks them. Solutions in `solutions/`.

## Analytical reading
`codebase-reading/README.md`, Day 1–2 section (`rich/text.py` slicing and `Text.__add__`).

## Build task (Day 2, 90 min)
Write `wordfreq.py`: read a text file path from `sys.argv`, print the top-N words with counts, ignoring case and punctuation. Use `Counter`, `str.translate` or `re`, and f-strings for aligned output. Then add a `--min-len` flag by hand-parsing `sys.argv` (you'll replace this with argparse on Day 5).
