"""Day 1 — core syntax. Run: python 01_basics.py"""

# --- numbers and strings -------------------------------------------------
n = 7
big = 2**100                # ints never overflow
print(n / 2, n // 2, n % 2, big)

name = "Ada"
greeting = f"Hello, {name}! You have {n:03d} messages."   # zero-padded to width 3
print(greeting)
print(f"{name!r} {3.14159:.2f} {0.256:.1%}")               # repr, precision, percent

multiline = """This
spans lines."""
print(multiline.upper().splitlines())

# --- truthiness -----------------------------------------------------------
for value in [0, 1, "", "x", [], [0], None, {}, {"a": 1}]:
    print(f"{value!r:>10} -> {bool(value)}")

items: list[int] = []
if not items:
    print("empty list is falsy")

x = None
if x is None:                # not `== None`
    print("use `is` for None")

# --- control flow ---------------------------------------------------------
for i in range(3):           # 0, 1, 2
    print(i, end=" ")
print()

for i in range(10, 0, -3):   # 10, 7, 4, 1
    print(i, end=" ")
print()

count = 0
while count < 3:
    count += 1               # no ++
else:                        # runs if loop wasn't broken out of
    print("while finished cleanly")

for i in range(10):
    if i == 2:
        continue
    if i == 4:
        break
    print("loop", i)

# ternary
label = "even" if n % 2 == 0 else "odd"
print(label)


# match (3.10+) — structural, not just switch
def describe(point: tuple[int, int]) -> str:
    match point:
        case (0, 0):
            return "origin"
        case (x, 0):
            return f"on x-axis at {x}"
        case (0, y):
            return f"on y-axis at {y}"
        case (x, y) if x == y:
            return "on diagonal"
        case _:
            return "somewhere"


print(describe((0, 0)), describe((3, 0)), describe((2, 2)), describe((1, 5)))

# --- slicing --------------------------------------------------------------
s = "python"
print(s[0], s[-1], s[1:4], s[:2], s[2:], s[::2], s[::-1])

nums = [10, 20, 30, 40, 50]
print(nums[1:-1], nums[::-1])
nums[1:3] = [99]             # slice assignment on lists
print(nums)

# --- unpacking ------------------------------------------------------------
a, b = 1, 2
a, b = b, a                  # swap
first, *middle, last = [1, 2, 3, 4, 5]
print(a, b, first, middle, last)

pairs = [("a", 1), ("b", 2)]
for key, val in pairs:
    print(key, val)

for i, ch in enumerate("abc", start=1):
    print(i, ch)

for left, right in zip([1, 2, 3], ["x", "y", "z"]):
    print(left, right)
