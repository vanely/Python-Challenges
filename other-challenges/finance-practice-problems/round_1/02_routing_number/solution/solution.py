"""
Problem 2 — Validate an ABA Routing Number (SOLUTION)

Clean the input, check it's exactly 9 digits, then apply the 3-7-1 checksum.
"""

# The weight for each of the 9 positions, from left to right.
# Writing them out like this is easier to read than slicing tricks.
WEIGHTS = [3, 7, 1, 3, 7, 1, 3, 7, 1]


def is_valid_routing_number(value):
    # Bad type (None, int, etc.)? Not valid, and we don't crash.
    if not isinstance(value, str):
        return False

    # Remove the spaces and dashes a person might type.
    cleaned = value.replace(" ", "").replace("-", "")

    # Must be exactly 9 characters, all digits.
    if len(cleaned) != 9 or not cleaned.isdigit():
        return False

    # Turn "011307129" into [0, 1, 1, 3, 0, 7, 1, 2, 9].
    digits = [int(char) for char in cleaned]

    # Multiply each digit by its weight and add everything up.
    total = 0
    for digit, weight in zip(digits, WEIGHTS):
        total += digit * weight

    # Valid when the total is a multiple of 10.
    return total % 10 == 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    assert is_valid_routing_number("011307129") is True      # Leader Bank
    assert is_valid_routing_number("011000015") is True      # Federal Reserve Bank of Boston
    assert is_valid_routing_number("011-307-129") is True    # dashes are ignored
    assert is_valid_routing_number(" 011 307 129 ") is True  # spaces are ignored

    assert is_valid_routing_number("011307128") is False     # checksum fails
    assert is_valid_routing_number("12345") is False         # too short
    assert is_valid_routing_number("0113071290") is False    # too long
    assert is_valid_routing_number("01130712A") is False     # has a letter
    assert is_valid_routing_number("") is False              # empty
    assert is_valid_routing_number(None) is False            # not a string
    assert is_valid_routing_number(11307129) is False        # an int lost its leading 0

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
