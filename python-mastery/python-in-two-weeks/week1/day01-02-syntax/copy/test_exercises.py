from collections import Counter

from exercises import (
    caesar, chunk, dedupe_preserving_order, fizzbuzz, flatten, group_by_first_letter,
    invert, is_palindrome, merge_defaults, parse_kv, running_total, second_largest,
    top_n, transpose, word_lengths,
)


def test_is_palindrome() -> None:
    assert is_palindrome("A man, a plan, a canal: Panama")
    assert not is_palindrome("python")


def test_fizzbuzz() -> None:
    assert fizzbuzz(15)[-1] == "FizzBuzz"
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]


def test_chunk() -> None:
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_flatten() -> None:
    assert flatten([[1, 2], [3], []]) == [1, 2, 3]


def test_word_lengths() -> None:
    assert word_lengths("Hi hi there") == {"hi": 2, "there": 5}


def test_top_n() -> None:
    c = Counter("a b b c c c d".split())
    assert top_n(c, 2) == ["c", "b"]
    assert top_n(Counter(["z", "a"]), 2) == ["a", "z"]


def test_group_by_first_letter() -> None:
    out = group_by_first_letter(["apple", "Banana", "avocado"])
    assert out == {"a": ["apple", "avocado"], "b": ["Banana"]}


def test_invert() -> None:
    assert invert({"a": 1, "b": 2}) == {1: "a", 2: "b"}


def test_running_total() -> None:
    assert running_total([1, 2, 3]) == [1, 3, 6]
    assert running_total([]) == []


def test_second_largest() -> None:
    assert second_largest([1, 5, 5, 3]) == 3
    assert second_largest([7, 7]) is None


def test_transpose() -> None:
    assert transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]


def test_dedupe() -> None:
    assert dedupe_preserving_order(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]


def test_parse_kv() -> None:
    assert parse_kv("a=1; b = 2;;") == {"a": "1", "b": "2"}


def test_merge_defaults() -> None:
    d = {"x": 1, "y": 2}
    o = {"y": 9}
    assert merge_defaults(d, o) == {"x": 1, "y": 9}
    assert d == {"x": 1, "y": 2}


def test_caesar() -> None:
    assert caesar("Hello, World!", 3) == "Khoor, Zruog!"
    assert caesar(caesar("abc xyz", 5), -5) == "abc xyz"
