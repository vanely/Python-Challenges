"""
Runs and checks every surprising claim in top_20_python_questions.md.

    python3 python_examples.py

Each section is numbered to match the question in the guide.
Change things and re-run to see what breaks.
"""

import copy
import functools
import platform
import sys
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


def check(label, condition):
    """Print a check mark for each claim; stop loudly if one is wrong."""
    assert condition, f"FAILED: {label}"
    print(f"  ok  {label}")


print("1. Tuples")
check("(5) is an int, not a tuple", isinstance((5), int))
check("(5,) is a tuple", isinstance((5,), tuple))
t = ([1, 2],)
t[0].append(3)  # the tuple can't change, but the list inside it can
check("a list inside a tuple can still change", t == ([1, 2, 3],))
check("tuples can be dict keys", {(1, 2): "ok"}[(1, 2)] == "ok")


print("2. Mutable default argument")
def add_fee(fee, fees=[]):
    fees.append(fee)
    return fees
add_fee(5)
check("the default list is shared across calls", add_fee(7) == [5, 7])
try:
    @dataclass
    class Bad:
        items: list = []
    check("dataclass should have refused a [] default", False)
except ValueError:
    check("dataclass refuses a mutable default", True)


print("3. Generators are single-use")
gen = (n * 2 for n in range(3))
check("first pass gives everything", list(gen) == [0, 2, 4])
check("second pass is empty", list(gen) == [])


print("4. Iterables vs iterators")
items = [1, 2, 3]
check("a list gives a NEW iterator each time", iter(items) is not iter(items))
it = iter(items)
check("an iterator's __iter__ returns itself", iter(it) is it)


print("5. Decorators")
def no_wraps(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
def with_wraps(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
@no_wraps
def fetch_a(): pass
@with_wraps
def fetch_b(): pass
check("without wraps, the name is lost", fetch_a.__name__ == "wrapper")
check("with wraps, the name is kept", fetch_b.__name__ == "fetch_b")

order = []
def tag(name):
    def decorator(func):
        order.append(name)   # runs at DEFINITION time, not call time
        return func
    return decorator
@tag("outer")
@tag("inner")
def stacked(): pass
check("decorators run at definition time, closest one first", order == ["inner", "outer"])


print("8. Keyword-only arguments")
def transfer(*, from_account, to_account, amount):
    return from_account, to_account, amount
try:
    transfer("A", "B", Decimal("50"))
    check("positional call should have failed", False)
except TypeError:
    check("keyword-only args refuse positional calls", True)


print("9. Copies, `is`, and the grid bug")
original = {"loans": [1, 2]}
shallow, deep = copy.copy(original), copy.deepcopy(original)
original["loans"].append(3)
check("shallow copy shares the inner list", shallow["loans"] == [1, 2, 3])
check("deep copy is independent", deep["loans"] == [1, 2])
grid = [[0] * 3] * 3
grid[0][0] = 1
check("[[0]*3]*3 shares one row three times", grid == [[1, 0, 0]] * 3)
if platform.python_implementation() == "CPython":
    check("small ints (<=256) are cached", int("256") is int("256"))
    check("larger ints are not", int("257") is not int("257"))


print("10. Dicts")
d = {1: "a", True: "b", 1.0: "c"}
check("1, True and 1.0 are the same key", d == {1: "c"} and len(d) == 1)
check("the first key (1) is the one kept", type(list(d)[0]) is int)


print("11. Late binding and UnboundLocalError")
funcs = [lambda: i for i in range(3)]
check("lambdas in a loop all see the last value", [f() for f in funcs] == [2, 2, 2])
funcs = [lambda i=i: i for i in range(3)]
check("a default argument freezes each value", [f() for f in funcs] == [0, 1, 2])
x = 10
def uses_x():
    print_me = x   # fails: the assignment below makes x local to the WHOLE function
    x = 5
    return print_me
try:
    uses_x()
    check("should have raised UnboundLocalError", False)
except UnboundLocalError:
    check("assigning anywhere makes the name local everywhere", True)


print("13. Exceptions")
class BankError(Exception): pass
class InsufficientFundsError(BankError): pass
try:
    try:
        raise TimeoutError("vendor slow")
    except TimeoutError as err:
        raise BankError("service unavailable") from err
except BankError as wrapped:
    check("`raise from` keeps the original cause", isinstance(wrapped.__cause__, TimeoutError))
check("custom hierarchy: catch the parent to catch children", issubclass(InsufficientFundsError, BankError))


print("14. classmethods respect subclasses")
class Loan:
    def __init__(self, principal):
        self.principal = principal
    @classmethod
    def from_dict(cls, data):
        return cls(Decimal(data["principal"]))
class JumboLoan(Loan): pass
check("JumboLoan.from_dict builds a JumboLoan", type(JumboLoan.from_dict({"principal": "900000"})) is JumboLoan)


print("15. MRO and super()")
calls = []
class A:
    def setup(self): calls.append("A")
class B(A):
    def setup(self): calls.append("B"); super().setup()
class C(A):
    def setup(self): calls.append("C"); super().setup()
class D(B, C):
    def setup(self): calls.append("D"); super().setup()
check("MRO is D, B, C, A, object", [k.__name__ for k in D.__mro__] == ["D", "B", "C", "A", "object"])
D().setup()
check("super() in B calls C (not A), and A runs once", calls == ["D", "B", "C", "A"])


print("16. dataclasses")
@dataclass
class Account:
    owner: str
    history: list = field(default_factory=list)
@dataclass(frozen=True)
class Money:
    amount: Decimal
check("each object gets its own fresh list", Account("a").history is not Account("b").history)
check("a regular dataclass is unhashable", Account.__hash__ is None)
check("a frozen dataclass is hashable", hash(Money(Decimal("1"))) is not None)


print("17. Stable sort")
loans = [("B", 2), ("A", 1), ("B", 1), ("A", 2)]
by_number = sorted(loans, key=lambda x: x[1])
by_letter_then_number = sorted(by_number, key=lambda x: x[0])   # sort twice, least important first
check("sorting twice gives a multi-key sort", by_letter_then_number == [("A", 1), ("A", 2), ("B", 1), ("B", 2)])


print("18. Reference counts")
thing = object()
check("getrefcount is at least 2 (the name + the argument)", sys.getrefcount(thing) >= 2)


print("19. Money and rounding")
check("floats are inexact", 0.1 + 0.2 != 0.3)
check("Decimals from strings are exact", Decimal("0.1") + Decimal("0.2") == Decimal("0.3"))
check("Decimal(0.1) exposes the float's error", str(Decimal(0.1)).startswith("0.1000000000000000055511"))
check("round() is banker's rounding: 2.5 -> 2", round(2.5) == 2)
check("round() is banker's rounding: 3.5 -> 4", round(3.5) == 4)
check("round(2.675, 2) is 2.67 (float stored as 2.67499...)", round(2.675, 2) == 2.67)
check("ROUND_HALF_UP gives 2.68",
      Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal("2.68"))
check("Decimal's default is also half-even: 2.665 -> 2.66",
      Decimal("2.665").quantize(Decimal("0.01")) == Decimal("2.66"))


print("\nAll claims checked.")
