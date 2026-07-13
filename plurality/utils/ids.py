"""Human-readable ID generation."""

import random
import string

_ALPHABET = string.ascii_lowercase + string.digits


def generate_hid(length: int = 6) -> str:
    """Generate a random human-readable ID."""
    return "".join(random.choices(_ALPHABET, k=length))


def snowflake_to_datetime(snowflake: int) -> float:
    """Convert Discord snowflake to Unix timestamp."""
    return ((snowflake >> 22) + 1420070400000) / 1000