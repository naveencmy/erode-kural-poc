"""Verhoeff Checksum Algorithm for Indian Aadhaar / UIDAI Validation."""

# The multiplication table (d)
_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# The permutation table (p)
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# The inverse table (inv)
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def validate_verhoeff(number_str: str) -> bool:
    """Validate that a number string passes the Verhoeff checksum algorithm.
    
    Aadhaar numbers are 12 digits where the final digit is a Verhoeff checksum.
    """
    clean_digits = "".join(filter(str.isdigit, str(number_str)))
    if len(clean_digits) != 12:
        return False

    c = 0
    reversed_digits = [int(x) for x in reversed(clean_digits)]

    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[i % 8][digit]]

    return c == 0


def generate_verhoeff(number_str: str) -> int:
    """Generate the Verhoeff check digit for an 11-digit number string."""
    clean_digits = "".join(filter(str.isdigit, str(number_str)))
    c = 0
    reversed_digits = [int(x) for x in reversed(clean_digits)]

    for i, digit in enumerate(reversed_digits):
        c = _D[c][_P[(i + 1) % 8][digit]]

    return _INV[c]
