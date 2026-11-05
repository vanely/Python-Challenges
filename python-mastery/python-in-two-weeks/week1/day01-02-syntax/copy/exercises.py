"""Day 1–2 exercises. Fill in each function. Run: pytest test_exercises.py

Rules: no imports beyond `collections` and `re`. Prefer comprehensions where they
read cleanly. Every function must type-check under `mypy --strict`.
"""
from collections import Counter


def is_palindrome(s: str) -> bool:
    """True if s reads the same backwards, ignoring case and non-letters."""
    raise NotImplementedError


def fizzbuzz(n: int) -> list[str]:
    """['1', '2', 'Fizz', '4', 'Buzz', ...] up to n."""
    raise NotImplementedError


def chunk(items: list[int], size: int) -> list[list[int]]:
    """chunk([1,2,3,4,5], 2) -> [[1,2],[3,4],[5]]. Use slicing."""
    raise NotImplementedError


def flatten(nested: list[list[int]]) -> list[int]:
    raise NotImplementedError


def word_lengths(text: str) -> dict[str, int]:
    """{'word': len} for each unique word (lowercased)."""
    raise NotImplementedError


def top_n(counts: Counter[str], n: int) -> list[str]:
    """The n most common keys, most common first. Ties: alphabetical."""
    raise NotImplementedError


def group_by_first_letter(words: list[str]) -> dict[str, list[str]]:
    """{'a': ['apple', 'avocado'], 'b': ['banana']}, keys lowercased. Use defaultdict."""
    raise NotImplementedError


def invert(d: dict[str, int]) -> dict[int, str]:
    raise NotImplementedError


def running_total(nums: list[int]) -> list[int]:
    """[1,2,3] -> [1,3,6]"""
    raise NotImplementedError


def second_largest(nums: list[int]) -> int | None:
    """None if fewer than two distinct values."""
    raise NotImplementedError


def transpose(matrix: list[list[int]]) -> list[list[int]]:
    """Use zip(*matrix)."""
    raise NotImplementedError


def dedupe_preserving_order(items: list[str]) -> list[str]:
    """Keep first occurrence. dict.fromkeys is the idiom."""
    raise NotImplementedError


def parse_kv(line: str) -> dict[str, str]:
    """'a=1;b=2' -> {'a':'1','b':'2'}. Ignore empty segments and whitespace."""
    raise NotImplementedError


def merge_defaults(defaults: dict[str, int], overrides: dict[str, int]) -> dict[str, int]:
    """Overrides win. Don't mutate inputs."""
    raise NotImplementedError


def caesar(text: str, shift: int) -> str:
    """Shift letters, preserve case, leave other chars. ord/chr and % 26."""
    raise NotImplementedError
