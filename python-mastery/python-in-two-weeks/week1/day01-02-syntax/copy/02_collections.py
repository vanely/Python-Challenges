"""Day 1 — list, tuple, dict, set, and the collections module."""
from collections import Counter, defaultdict, deque

# --- list ---------------------------------------------------------------
xs = [3, 1, 2]
xs.append(4)
xs.extend([5, 6])
xs.insert(0, 0)
xs.remove(3)                     # by value, first occurrence
popped = xs.pop()                # last
print(xs, popped, len(xs), 2 in xs)
xs.sort()                        # in place, returns None  <-- common bug: y = xs.sort()
ys = sorted(xs, reverse=True)    # returns new list
print(xs, ys)

words = ["banana", "Apple", "cherry"]
print(sorted(words, key=str.lower))
print(sorted(words, key=len))
print(max(words, key=len))

# --- tuple: immutable record ---------------------------------------------
point = (3, 4)
x, y = point
single = (5,)                    # trailing comma makes a 1-tuple
print(x, y, single, point[0])

# --- dict --------------------------------------------------------------
user = {"id": 1, "name": "Ada", "tags": ["admin"]}
user["email"] = "ada@example.com"
print(user["name"], user.get("phone"), user.get("phone", "n/a"))
print(list(user.keys()), list(user.values()))
for k, v in user.items():
    print(f"{k}={v}")
merged = {**user, "name": "Grace"}          # spread; later wins
merged2 = user | {"id": 2}                  # 3.9+
print(merged["name"], merged2["id"])
del user["tags"]
print("tags" in user)
print(user.pop("email"), user.setdefault("role", "viewer"), user)

# --- set ---------------------------------------------------------------
a = {1, 2, 3}
b = {3, 4}
print(a | b, a & b, a - b, a ^ b)
a.add(9)
a.discard(42)                    # no error if missing; .remove raises
print(a, 2 in a)
uniq = set("mississippi")
print(sorted(uniq))

# --- Counter -----------------------------------------------------------
text = "the quick the lazy the end"
counts = Counter(text.split())
print(counts, counts.most_common(2), counts["the"], counts["missing"])

# --- defaultdict -------------------------------------------------------
groups: defaultdict[int, list[str]] = defaultdict(list)
for word in ["a", "bb", "cc", "ddd"]:
    groups[len(word)].append(word)
print(dict(groups))

# --- deque -------------------------------------------------------------
window: deque[int] = deque(maxlen=3)
for i in range(6):
    window.append(i)
print(window)                    # deque([3, 4, 5], maxlen=3)
q: deque[str] = deque(["a", "b"])
q.appendleft("z")
print(q.popleft(), q)
