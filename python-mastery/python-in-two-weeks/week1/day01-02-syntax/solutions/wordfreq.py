"""Day 2 build task — reference solution.

Usage: python wordfreq.py FILE [N] [--min-len K]
"""
import re
import sys
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


def top_words(text: str, n: int, min_len: int) -> list[tuple[str, int]]:
    words = (w for w in WORD.findall(text.lower()) if len(w) >= min_len)
    return Counter(words).most_common(n)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: wordfreq.py FILE [N] [--min-len K]", file=sys.stderr)
        return 2
    min_len = 1
    if "--min-len" in argv:
        i = argv.index("--min-len")
        min_len = int(argv[i + 1])
        del argv[i : i + 2]
    path = Path(argv[0])
    n = int(argv[1]) if len(argv) > 1 else 10
    text = path.read_text(encoding="utf-8")
    rows = top_words(text, n, min_len)
    width = max((len(w) for w, _ in rows), default=4)
    for word, count in rows:
        print(f"{word:<{width}}  {count:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
