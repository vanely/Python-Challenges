# ------------------------Numbers and Strings------------------------
n = 7
bigNum = 2**100

print("normal division: ", n / 2, "\nfloor division: ", n // 2, "\nmodulus: ", n % 2,"\nbigNum: ", bigNum)
print("____________________________________________")

name = "Ada"
greeting = f"hello {name}! You have {n:03d}, messages."
print(greeting)
print(f"{name!r} {3.14159:.2f} {0.256:.2%}")
print("____________________________________________")

multiline = """This text
spans more
than one line."""
print(multiline.upper().splitlines())
print("____________________________________________")

# ------------------------Truthies------------------------
for value in [0, 1, "", "x", [], [0], None, {}, {"a": 1}]:
  print(f"{value!r:>10} -> {bool(value)}")

print("____________________________________________")
items: list[int] = []
if not items:
  print("empty list is falsy")

x = None
if x is None:
  print(f"use {"is"!r} for None")

print("____________________________________________")
# ------------------------Control Flow------------------------
for i in range(3):
  print(i, end=" ")
print()

for i in range(10, 0, -3):
  print(i, end=" ")
print()

count = 0
while count < 3:
  count += 1
else:
  print("while finished cleanly")

for i in range(10):
  if i == 2:
    continue
  if i == 4:
    print(f"{"loop":>5} {i}")

num_val: int = 353
label: str = "even" if num_val % 2 == 0 else "odd" 
print(label)

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

tupi: tuple[int, int] = (34, 9)
print(F"tuple: {tupi}")

# ------------------------Unpacking------------------------
a, b = 1, 2
a, b = b, a

""" 
'*' captures everthing except the first and last items if used on middle,
it gets everthing except for the last if used as first,
and everything except the first if used for the last, 
and also considers what first and last are if there are three vs two unpacking vars
"""
first, *middle, last = [1, 2, 2.5, 2.9, 3, 3.5, 3.9, 4, 5] 
print(a, b, first, middle, last)

pairs: list[tuple[str, int]] = [("a", 1), ("b", 2)]
for key, val in pairs:
  print(key, val)

print("____________________________________________")
for i, ch in enumerate(["apple", "banana", "pear", "guava", "plum", "tangerine", "grape"], start=1):
  print(i, ch)

"""
zip() merges two iterables(lists, tuples, strings), 
and creates tuples based on their positional index
ex: list(zip([1, 2, 3], ["x", "y", "z"])) == [(1, "x"), (2, "y"), (3, "z")]
"""
pants = zip([1,2,3], ["x", "y", "z"])
for left, right in pants:
  print(f"{left} - {right}")
