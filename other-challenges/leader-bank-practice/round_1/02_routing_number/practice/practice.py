"""
Problem 2 — Validate an ABA Routing Number (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

WEIGHTS = [3, 7, 1, 3, 7, 1, 3, 7, 1]


def is_valid_routing_number(value):
    # TODO: return False if value isn't a string
    # TODO: strip spaces and dashes
    # TODO: return False unless it's exactly 9 digits
    # TODO: multiply each digit by its weight, sum, check total % 10 == 0
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change these.
# ---------------------------------------------------------------------------
def run_tests():
    assert is_valid_routing_number("011307129") is True
    assert is_valid_routing_number("011000015") is True
    assert is_valid_routing_number("011-307-129") is True
    assert is_valid_routing_number(" 011 307 129 ") is True

    assert is_valid_routing_number("011307128") is False
    assert is_valid_routing_number("12345") is False
    assert is_valid_routing_number("0113071290") is False
    assert is_valid_routing_number("01130712A") is False
    assert is_valid_routing_number("") is False
    assert is_valid_routing_number(None) is False
    assert is_valid_routing_number(11307129) is False

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
