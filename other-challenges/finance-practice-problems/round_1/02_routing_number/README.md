# Problem 2 — Validate an ABA Routing Number

Every US bank has a 9-digit **ABA routing number**. The last digit is a check digit: it catches typos.

Number the digits `d1 … d9`, left to right. The number is valid when

```
3 × (d1 + d4 + d7)  +  7 × (d2 + d5 + d8)  +  1 × (d3 + d6 + d9)
```

is evenly divisible by 10.

Write `is_valid_routing_number(value)` that returns `True` or `False`.

## Rules

- The input is a **string**. (Why not an int? Routing numbers can start with `0`, and an int would drop the leading zero.)
- Ignore spaces or dashes a user might type: `"011-307-129"` is fine.
- Anything that isn't exactly 9 digits after cleaning is invalid.
- Never crash on bad input. Return `False` instead.

## Examples

| Input | Valid? | Why |
|---|---|---|
| `"011307129"` | ✅ | Leader Bank's routing number: 3×4 + 7×3 + 17 = 50 |
| `"011307128"` | ❌ | Same number with the last digit changed: total is 49 |
| `"12345"` | ❌ | Not 9 digits |
| `"01130712A"` | ❌ | Contains a letter |
| `None` | ❌ | Not a string |

## Things to talk about

- Why 3, 7, 1? The uneven weights catch most single-digit typos and most swaps of neighboring digits.
- Passing the checksum doesn't mean the bank exists. A real system would also look the number up in the Fed's directory.
