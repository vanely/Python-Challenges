# Top 20 Python Interview Questions — Explained in Depth

Each question has:
- **Say this first:** a 1–2 sentence answer to open with
- **The deeper explanation**
- **Where it shows up in real work**
- **💡 The detail most people don't know:** your chance to stand out

Every surprising claim marked 💡 is checked in `python_examples.py`. Run it and change the code to see what happens.

---

## 1. What's the difference between a list and a tuple?

**Say this first:** A list can be changed after it's created (*mutable*); a tuple can't (*immutable*). Use a tuple for a fixed record, like a `(lat, lon)` pair, and a list for a collection that grows or changes.

**Deeper:**
- Because tuples can't change, a tuple can be a **dict key or a set member**, as long as everything inside it can be too. A list never can.
- Tuples are a little smaller in memory and a little faster to create. Python can even build constant tuples once, when the code is compiled.
- "Immutable" applies only to the tuple itself. `t = ([1, 2],)` can't swap out its list, but the list *inside* can still change: `t[0].append(3)` works.
- `collections.namedtuple` and `typing.NamedTuple` give tuple fields names: `point.lat` instead of `point[0]`.

**Real work:** returning several values from a function (`return balance, status` is a tuple), using composite dict keys like `{(account_id, date): total}`, and database rows (most drivers return tuples).

💡 **The comma makes the tuple, not the parentheses.** `(5)` is just the number 5. `(5,)` is a one-item tuple. `x = 1, 2` is also a tuple, with no parentheses at all.

---

## 2. What is the mutable default argument trap?

**Say this first:** Default values are created **once, when the function is defined**, not each time it's called. So a default list or dict is *shared* across every call. Use `None` as the default and create the list inside the function.

```python
def add_fee(fee, fees=[]):        # BUG: one shared list
    fees.append(fee)
    return fees

add_fee(5)   # [5]
add_fee(7)   # [5, 7]   <- surprise: the list from the first call is back

def add_fee(fee, fees=None):      # FIX
    if fees is None:
        fees = []
    fees.append(fee)
    return fees
```

**Deeper:** a `def` statement runs once and evaluates its defaults right then. They're stored on the function object (`add_fee.__defaults__`). Every call that doesn't pass `fees` gets that same stored list.

**Real work:** a classic source of "data from one request showing up in another" bugs in web servers, because the server process lives a long time.

💡 **`dataclasses` won't let you make this mistake:** `x: list = []` raises a `ValueError` when the class is defined. You must write `x: list = field(default_factory=list)`, which creates a fresh list for every object.

---

## 3. What is a generator, and why use one?

**Say this first:** A generator is a function that uses `yield` to produce values **one at a time, on demand**, pausing between them. It uses almost no memory no matter how much data it produces, so it's ideal for big files or paged API results.

```python
def read_transactions(path):
    with open(path) as f:
        for line in f:                 # one line in memory at a time
            yield parse(line)

total = sum(t.amount for t in read_transactions("big.csv"))   # generator expression
```

**Deeper:**
- Calling a generator function **doesn't run it**. It returns a generator object. The code runs only when you ask for the next value (`next()`, a `for` loop, `sum()`).
- At each `yield`, the function **pauses with all its local variables kept**, then resumes there next time.
- `yield from other_generator()` hands off to another generator.
- `(x for x in items)` with parentheses is a generator expression, the lazy cousin of a list comprehension.

**Real work:**
- Reading a 5 GB transaction file line by line
- Streaming every page of an API without holding them all (Round 1, problem 8 could `yield` each page's records)
- Data pipelines that chain several steps

💡 **A generator can only be used once.** After it's used up, it stays empty: `list(gen)` gives everything the first time and `[]` the second time. This quietly breaks code that loops over the same generator twice.

---

## 4. Iterable vs. iterator: what's the difference?

**Say this first:** An **iterable** is anything you can loop over (list, dict, file). An **iterator** is the object that actually does the looping and remembers where it is. `iter(iterable)` gives you an iterator, and `next(iterator)` gives you the next item until it raises `StopIteration`.

**Deeper:** a `for` loop is shorthand for:
```python
it = iter(items)
while True:
    try:
        item = next(it)
    except StopIteration:
        break
    ...
```
- A class becomes iterable by defining `__iter__`.
- An iterator also defines `__next__`.
- Generators are iterators automatically.

**Real work:** writing a class like `LoanPortfolio` that you can loop over directly: `for loan in portfolio:`.

💡 **A list can be looped over many times; an iterator can't.** Each `iter(my_list)` creates a *new* iterator starting at the beginning. An iterator's own `__iter__` just returns *itself*, already part-way through. That's the root reason behind question 3's "use once" behavior.

---

## 5. What is a decorator? How would you write one?

**Say this first:** A decorator is a function that **takes a function and returns an improved version of it**, adding behavior like logging, timing, retries, or permission checks without changing the original code. `@my_decorator` above a `def` is shorthand for `func = my_decorator(func)`.

```python
import functools, time

def retry(times=3, delay=0.5):                 # 1. takes the settings
    def decorator(func):                       # 2. takes the function
        @functools.wraps(func)                 #    keeps func's name and docstring
        def wrapper(*args, **kwargs):          # 3. runs on every call
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except ConnectionError:
                    if attempt == times - 1:
                        raise
                    time.sleep(delay * 2 ** attempt)
        return wrapper
    return decorator

@retry(times=3)
def fetch_loan(loan_id): ...
```

**Deeper:**
- A decorator *with settings* has **three layers**: the settings, the function, the wrapper.
- Without `functools.wraps`, the wrapped function's `__name__` becomes `"wrapper"`, which makes logs and debugging confusing.

**Real work:** Django's `@login_required`, `@transaction.atomic`, Flask's `@app.route`, `@functools.lru_cache`, `@pytest.fixture`, and a homegrown `@retry` or `@timed`.

💡 **Decorators run when the module is imported, not when the function is called.** That's why Flask's `@app.route` can register URLs just by your file being imported.
💡 **When you stack decorators, the one closest to the `def` is applied first.** `@a` above `@b` means `a(b(func))`.

---

## 6. What is the GIL?

**Say this first:** The **Global Interpreter Lock** is a lock inside standard Python (CPython) that lets only **one thread run Python code at a time**. Threads still help for **I/O-bound** work like waiting on networks, files, or databases, because the lock is released while waiting. For **CPU-bound** work like heavy math, use multiple *processes* instead.

**Deeper:**
- The GIL makes Python's internal memory management simple and safe.
- It's released during I/O and by many C extensions (NumPy does heavy math without holding it).
- That's why `ThreadPoolExecutor` speeds up 50 API calls but not 50 big calculations.
- Newer Python versions offer a **"free-threaded" build without the GIL**. It started as experimental in 3.13 and became officially supported, though not the default, in 3.14. Mentioning it shows you're current.

**Real work:** calling 20 vendor APIs at once works well with threads or asyncio. Number-crunching an amortization model for 100,000 loans would use `multiprocessing` or NumPy.

💡 **The GIL does NOT make your code thread-safe.** `counter += 1` is several steps (read, add, write), and Python can switch threads between them. Two threads can still lose updates, so shared state still needs a `threading.Lock`.

---

## 7. Threading vs. multiprocessing vs. asyncio: when do you use each?

**Say this first:**
- **asyncio:** lots of waiting (thousands of network calls), one thread taking turns.
- **Threading:** some waiting, or libraries that aren't async.
- **Multiprocessing:** heavy CPU work, using several CPU cores at once.

| | Threading | Multiprocessing | asyncio |
|---|---|---|---|
| Good for | I/O-bound | CPU-bound | Lots of I/O-bound tasks |
| Runs in parallel? | No (GIL) | Yes, separate processes | No, one thread takes turns |
| Memory | Shared | Separate (data copied between processes) | Shared |
| Gotcha | Race conditions | Startup cost; data must be picklable | One blocking call freezes everything |

**Deeper:**
- **Concurrency** means juggling several tasks; **parallelism** means doing several at the exact same moment.
- asyncio is *cooperative*: each task must `await` to give others a turn.
- `concurrent.futures` (`ThreadPoolExecutor`, `ProcessPoolExecutor`) gives threads and processes the same simple interface.

**Real work:** FastAPI uses asyncio. A nightly batch that pulls 5,000 loan records from an API could use a thread pool, with a cap on workers so you don't break the vendor's rate limit.

💡 **Calling `time.sleep()` inside an `async def` freezes every other task**, because it blocks the one shared thread. Use `await asyncio.sleep()`. The same goes for blocking libraries like `requests`; use `httpx` or `aiohttp` instead.

---

## 8. Explain `*args`, `**kwargs`, keyword-only and positional-only arguments.

**Say this first:** `*args` collects extra positional arguments into a tuple; `**kwargs` collects extra named arguments into a dict. A bare `*` in the argument list means everything after it **must be passed by name**, and a `/` means everything before it **must be passed by position**.

```python
def transfer(*, from_account, to_account, amount):   # all keyword-only
    ...

transfer(from_account="A", to_account="B", amount=Decimal("50"))   # OK
transfer("A", "B", Decimal("50"))                                  # TypeError
```

**Deeper:**
- `*` and `**` also **unpack** when *calling*: `f(*my_list, **my_dict)`.
- `*args`/`**kwargs` are how decorators pass along any arguments untouched (see question 5).

**Real work:** keyword-only arguments for money functions. With `transfer("A", "B", 50)` it's easy to swap the accounts and send money the wrong way. Requiring names makes that mistake impossible.

💡 **Positional-only (`/`)** lets a library rename a parameter later without breaking anyone, because nobody could have passed it by name. Many built-ins work this way: `len(obj=[1])` is an error.

---

## 9. `is` vs `==`, and shallow vs. deep copy?

**Say this first:** `==` asks "**equal value**?"; `is` asks "**the exact same object** in memory?" Use `is` only for `None` (and similar one-of-a-kind values). A **shallow copy** copies the outer container but shares the items inside; a **deep copy** copies everything, all the way down.

```python
import copy
original = {"loans": [1, 2]}
shallow = copy.copy(original)
deep = copy.deepcopy(original)
original["loans"].append(3)
shallow["loans"]   # [1, 2, 3]  <- shared inner list
deep["loans"]      # [1, 2]     <- fully independent
```

**Real work:** copying a config or default template before changing it for one customer. A shallow copy would quietly change the template for everyone.

💡 **The "grid" bug:** `[[0] * 3] * 3` makes three references to the *same* row, so setting `grid[0][0] = 1` changes every row. Use `[[0] * 3 for _ in range(3)]`.
💡 **CPython keeps one shared copy of the small integers -5 to 256**, so `int("256") is int("256")` is `True` but `int("257") is int("257")` is `False`. That's why `is` must never be used to compare numbers.

---

## 10. How do dictionaries work, and what's their time complexity?

**Say this first:** A dict is a **hash table**. Python hashes the key to jump straight to its slot, so lookup, insert, and delete are **O(1) on average**. Keys must be *hashable* (immutable things like str, int, tuple). Since Python 3.7, dicts **keep insertion order**, and that's guaranteed by the language.

**Deeper:**
- Two keys that are equal **must** have the same hash. If you define `__eq__` on a class, define `__hash__` too, or the class becomes unhashable.
- Collisions (different keys landing on the same slot) are handled internally. The worst case is O(n), but that's rare.
- `defaultdict`, `Counter`, and `OrderedDict` (still useful for `move_to_end`) live in `collections`.

**Real work:** caching, grouping (`defaultdict(list)`), counting (`Counter`), and quick lookups such as "is this event ID already processed?"

💡 **`1`, `1.0`, and `True` are the same dict key**, because they're equal and hash the same. `{1: "a", True: "b"}` becomes `{1: "b"}`, a single entry. The first key is kept and the value is overwritten.

---

## 11. Explain scope (LEGB), closures, and the late-binding trap.

**Say this first:** Python looks up names in four places, in order: **L**ocal, **E**nclosing function, **G**lobal (module), **B**uilt-in. A **closure** is an inner function that remembers variables from the outer function even after the outer function has finished.

```python
def make_fee_calculator(rate):
    def calc(amount):
        return amount * rate      # `rate` is remembered from the outer function
    return calc

wire_fee = make_fee_calculator(Decimal("0.01"))
```

**Deeper:**
- To *reassign* an outer variable, you need `nonlocal` (for an enclosing function) or `global` (for the module). Just reading it needs nothing.
- Closures are how decorators remember the function they wrap.

💡 **Late binding:** closures remember the *variable*, not its value at that moment.
```python
funcs = [lambda: i for i in range(3)]
[f() for f in funcs]     # [2, 2, 2], not [0, 1, 2]
funcs = [lambda i=i: i for i in range(3)]   # fix: freeze the value as a default
```
💡 **`UnboundLocalError`:** if a function assigns to a name *anywhere* in its body, that name is local for the **whole** function, even on lines before the assignment. So `print(x); x = 5` inside a function fails, even if a global `x` exists.

---

## 12. What is a context manager?

**Say this first:** A context manager handles **setup and guaranteed cleanup** around a block of code using `with`. The classic example: `with open(f) as file:` closes the file even if an error happens inside. You can write one as a class (`__enter__` / `__exit__`) or, more easily, with `@contextlib.contextmanager`.

```python
from contextlib import contextmanager

@contextmanager
def db_transaction(conn):
    try:
        yield conn            # the code inside the `with` block runs here
        conn.commit()         # no errors -> save
    except Exception:
        conn.rollback()       # any error -> undo everything
        raise
```

**Real work:**
- Database transactions (all-or-nothing transfers, like Round 1, problem 3)
- Locks (`with lock:`)
- Temporary settings: `decimal.localcontext()` changes Decimal precision only inside the block
- Timing a block of code

💡 **If `__exit__` returns `True`, the exception is silently swallowed.** That's powerful but dangerous. `contextlib.suppress(FileNotFoundError)` uses it on purpose to ignore one specific error.

---

## 13. How should you handle exceptions well?

**Say this first:**
- Catch **specific** exceptions, never a bare `except:`.
- Create custom exceptions for your business errors (`InsufficientFundsError`).
- Use `raise ... from err` to keep the original cause.
- Use `finally` for cleanup that must always happen.

```python
try:
    data = fetch_loan(loan_id)
except TimeoutError as err:
    raise LoanServiceUnavailable(loan_id) from err   # keeps the original traceback
else:
    save(data)        # runs only if NO exception happened
finally:
    close_connection()  # always runs
```

**Deeper:**
- **EAFP** ("easier to ask forgiveness than permission"): just try it and catch the error. This is the Python style, versus checking everything first (**LBYL**, "look before you leap").
- A custom exception *hierarchy* (`BankError` → `InsufficientFundsError`, `AccountFrozenError`) lets callers catch broadly or narrowly.

**Real work:** splitting retryable from non-retryable errors (`TransientAPIError` vs `PermanentAPIError` in Round 1, problem 8).

💡 **A bare `except:` also catches `KeyboardInterrupt` and `SystemExit`**, so Ctrl+C may not stop your program. `except Exception:` avoids that.
💡 **A `return` inside `finally` throws away any exception from the `try` block.** It's so error-prone that newer Python versions warn about it.

---

## 14. Instance methods vs. `@classmethod` vs. `@staticmethod`, and `@property`?

**Say this first:**
- **Instance method:** gets `self`, works on one object.
- **Class method:** gets `cls`, works on the class. Mainly used for **alternative constructors**.
- **Static method:** gets neither. It's a plain function kept inside the class for organization.
- **`@property`:** makes a method look like an attribute, often to make something read-only or calculated.

```python
class Loan:
    def __init__(self, principal, rate):
        self.principal, self.rate = principal, rate

    @classmethod
    def from_dict(cls, data):                  # alternative constructor
        return cls(Decimal(data["principal"]), Decimal(data["rate"]))

    @staticmethod
    def monthly_rate(annual):                  # helper, no self needed
        return annual / 12

    @property
    def annual_interest(self):                 # loan.annual_interest, no ()
        return self.principal * self.rate
```

**Real work:** `datetime.fromisoformat(...)` and `dict.fromkeys(...)` are classmethods. Round 1, problem 3 used `@property` so `balance` can't be set from outside.

💡 **Classmethods respect subclasses.** Because `from_dict` calls `cls(...)` and not `Loan(...)`, calling `JumboLoan.from_dict(...)` correctly builds a `JumboLoan`.

---

## 15. How does inheritance work? What's the MRO and `super()`?

**Say this first:** A class can inherit from one or more parents. The **MRO (Method Resolution Order)** is the order Python searches classes for a method. `super()` calls the **next class in the MRO**, which isn't always the direct parent.

```python
class A: ...
class B(A): ...
class C(A): ...
class D(B, C): ...
D.__mro__   # D -> B -> C -> A -> object
```

**Deeper:**
- Python builds the MRO with the **C3 linearization** rule: children come before parents, and the left-to-right order you listed is kept.
- **Mixins** are small classes that add one ability (like `JsonSerializableMixin`), meant to be combined.
- **Composition over inheritance:** often a class should *have* a helper object rather than *be* a subtype. That's easier to test and change.

**Real work:** Django class-based views and DRF serializers rely heavily on mixins and the MRO.

💡 **In the diamond above, `super()` inside `B` calls `C`, not `A`**, even though `B` only inherits from `A`. That's what lets every class in a diamond run its setup exactly once.

---

## 16. dataclasses, type hints, and Pydantic?

**Say this first:** **Type hints** (`amount: Decimal`) document types for tools like editors and `mypy`, but **Python doesn't enforce them at runtime**. **`@dataclass`** writes `__init__`, `__repr__`, and `__eq__` for you. **Pydantic** actually *validates and converts* data at runtime, which makes it the right tool for untrusted input like API responses and LLM output.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)          # frozen: can't change after creation, and hashable
class Money:
    amount: Decimal
    currency: str = "USD"

@dataclass
class Account:
    owner: str
    history: list = field(default_factory=list)   # fresh list per object
```

**Real work:**
- dataclasses for internal records.
- Pydantic at the edges of your system: requests coming in, vendor responses, LLM JSON (Design 2).
- FastAPI is built on Pydantic.

💡 **A regular (not frozen) dataclass is unhashable.** Because it defines `__eq__` and the object can change, Python sets `__hash__ = None`, so you can't put it in a set. `frozen=True` fixes that.
💡 `@dataclass(slots=True)` (Python 3.10+) uses less memory and blocks typo-attributes like `acct.balence = 5`.

---

## 17. What are the time complexities of the built-in operations?

**Say this first:** the ones to know cold:

| Operation | Cost | Note |
|---|---|---|
| `list.append`, `list.pop()` (from the end) | O(1) | |
| `list.insert(0, x)`, `list.pop(0)` | **O(n)** | everything shifts. Use `collections.deque` |
| `x in list` | **O(n)** | scans every item |
| `x in set`, `x in dict` | O(1) average | hash lookup |
| `list.sort()` / `sorted()` | O(n log n) | |
| `heapq.heappush` / `heappop` | O(log n) | for "top k" or priority queues |
| String concatenation in a loop | can be O(n²) | use `"".join(parts)` |

**Real work:**
- Checking "have I seen this ID?" against a list of a million IDs is slow; a set is instant.
- A sliding-window deque (Round 1, problem 6) keeps both ends O(1).

💡 **Python's sort (Timsort) is stable**: equal items keep their original order. So you can sort by several keys by sorting **twice**, least important key first.
💡 **On data that's already sorted, Timsort is O(n)**, because it spots runs that are already in order.

---

## 18. How does Python manage memory?

**Say this first:** Mostly by **reference counting**. Every object counts how many names point to it, and it's freed the moment that count hits zero. A **cycle-detecting garbage collector** cleans up the leftovers: objects that only point to each other.

**Deeper:**
- `del x` removes the *name* `x`, not necessarily the object. Another reference may still keep it alive.
- **`__slots__`** stops a class from giving each object its own `__dict__`, which saves a lot of memory across millions of objects.
- **`weakref`** points to an object *without* keeping it alive. It's useful for caches.
- **Memory leaks in Python** usually mean something is still holding a reference: a global cache that never empties, or a list that keeps growing.

**Real work:** a long-running worker whose memory keeps growing usually has an unbounded cache. Fix it with `functools.lru_cache(maxsize=...)` or a TTL.

💡 **`sys.getrefcount(x)` always reports one more than you'd expect**, because passing `x` into the function creates a temporary reference.

---

## 19. Why not use floats for money? How does `Decimal` rounding work?

**Say this first:** Floats are stored in binary, which can't represent most decimal fractions exactly. That's why `0.1 + 0.2` gives `0.30000000000000004`. For money, use **`Decimal` built from strings**, and round explicitly with `quantize` and a named rounding rule.

```python
from decimal import Decimal, ROUND_HALF_UP
Decimal("0.1") + Decimal("0.2")            # Decimal('0.3')  exact
Decimal(0.1)                               # Decimal('0.1000000000000000055511151231257827...')  <- the float's error, made visible
Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)   # Decimal('2.68')
```

**Deeper:**
- `Decimal` arithmetic uses a context: 28 significant digits by default, adjustable with `decimal.localcontext()`.
- Databases have the same issue: use `NUMERIC(12, 2)`, never `FLOAT`, for money columns.
- Store money as integer cents, or as Decimal. Never as float.

💡 **Python's default rounding is "banker's rounding" (round half to even)**, both in built-in `round()` and in Decimal's default context.
- `round(2.5)` is `2` and `round(3.5)` is `4`.
- Exact halves go to the nearest *even* number, so rounding errors don't all lean the same way across millions of transactions.
- If the business rule says "half up," you must ask for `ROUND_HALF_UP` explicitly.

💡 `round(2.675, 2)` gives `2.67`, not `2.68`. The float `2.675` is really stored as `2.67499999...`.

---

## 20. How do you test Python code? What about mocking?

**Say this first:**
- I use **pytest**: plain `assert` statements, **fixtures** for setup, and **`@pytest.mark.parametrize`** to run one test over many inputs.
- For outside dependencies like APIs, databases, and time, I prefer **dependency injection** (passing them in) over mocking. Where I do mock, I use `unittest.mock.patch`.

```python
import pytest

@pytest.mark.parametrize("routing, expected", [
    ("011307129", True),
    ("011307128", False),
    ("", False),
])
def test_routing(routing, expected):
    assert is_valid_routing_number(routing) is expected
```

**Deeper:**
- **Unit tests** check one function, fast, with no network.
- **Integration tests** use a real database or a vendor sandbox.
- Aim for many unit tests and fewer integration tests.
- **Dependency injection** (passing `fetch_page` and `sleep` into the function, as in Round 1, problem 8) makes code testable without any mocking library.
- Test the **edge cases**: empty input, `None`, duplicates, boundaries (exactly 24 hours, exactly the balance).

**Real work:** a fake Encompass client for testing the integration worker (Design 1), and a "golden dataset" test for AI extraction (Design 2).

💡 **Patch where the name is *used*, not where it's *defined*.** If `billing.py` does `from requests import get`, you must patch `"billing.get"`, not `"requests.get"`. `billing` already has its own copy of the name. This trips up even experienced developers.
💡 pytest rewrites `assert` statements so that a failure shows the actual values on both sides. That's why plain `assert` is enough there.
