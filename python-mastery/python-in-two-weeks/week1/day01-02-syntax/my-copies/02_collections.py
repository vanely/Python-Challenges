from collections import Counter, defaultdict, deque

# --- list ---------------------------------------------------------------
xs: list[int] = [3, 1, 2, 8734]
xs.append(4)
xs.extend([5, 6])
xs.insert(0, 0)
xs.remove(3)
xs.insert(3, 98032409) # inserts at index 3

popped = xs.pop()
print(xs, popped, len(xs), "true" if 2 in xs else "false")

print("____________________________________________")
xs.sort()
print(xs)

ys = sorted(xs, reverse=True)
print(f"sorted: {xs}\nreverse sorted: {ys}")

print("____________________________________________")
words: list[str] = ["banana", "apple", "cherry"]
print(sorted(words, key=str.lower))
print(sorted(words, key=len))
print(max(words, key=len))

inventory = [
    ("Laptop", "Electronics", 1200),
    ("Phone", "Electronics", 800),
    ("Desk", "Furniture", 250),
    ("Chair", "Furniture", 150),
]

# Sort by Category alphabetically, then by Price ascending
# don't need to pass two items to the lambda, can just choose index that you want to sort by.
sorted_inv = sorted(inventory, key=lambda item: (item[0]))
print(sorted_inv)


# --- tuple: immutable record ---------------------------------------------
point = (3, 4)
x, y = point