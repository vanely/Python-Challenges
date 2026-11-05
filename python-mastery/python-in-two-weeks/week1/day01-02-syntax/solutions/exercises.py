"""Reference solutions — Day 1–2."""
import re
from collections import Counter, defaultdict


def is_palindrome(s: str) -> bool:
    cleaned = [ch.lower() for ch in s if ch.isalpha()]
    return cleaned == cleaned[::-1]


def fizzbuzz(n: int) -> list[str]:
    return [
        "FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i)
        for i in range(1, n + 1)
    ]


def chunk(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def flatten(nested: list[list[int]]) -> list[int]:
    return [x for row in nested for x in row]


def word_lengths(text: str) -> dict[str, int]:
    return {w.lower(): len(w) for w in text.split()}


def top_n(counts: Counter[str], n: int) -> list[str]:
    return [k for k, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def group_by_first_letter(words: list[str]) -> dict[str, list[str]]:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for w in words:
        groups[w[0].lower()].append(w)
    return dict(groups)


def invert(d: dict[str, int]) -> dict[int, str]:
    return {v: k for k, v in d.items()}


def running_total(nums: list[int]) -> list[int]:
    out: list[int] = []
    acc = 0
    for n in nums:
        acc += n
        out.append(acc)
    return out


def second_largest(nums: list[int]) -> int | None:
    distinct = sorted(set(nums), reverse=True)
    return distinct[1] if len(distinct) >= 2 else None


def transpose(matrix: list[list[int]]) -> list[list[int]]:
    return [list(col) for col in zip(*matrix)]


def dedupe_preserving_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def parse_kv(line: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for seg in line.split(";"):
        if "=" not in seg:
            continue
        k, v = seg.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def merge_defaults(defaults: dict[str, int], overrides: dict[str, int]) -> dict[str, int]:
    return {**defaults, **overrides}


def caesar(text: str, shift: int) -> str:
    def rot(ch: str) -> str:
        if not ch.isalpha():
            return ch
        base = ord("A") if ch.isupper() else ord("a")
        return chr((ord(ch) - base + shift) % 26 + base)

    return "".join(rot(ch) for ch in text)


_ = re  # kept importable for experiments
