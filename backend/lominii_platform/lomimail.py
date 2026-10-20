"""
Lomimail identity and placement utilities.

This module is intentionally independent of the database and
authentication routes. It does not establish verified identity.
"""

import re
import unicodedata
from collections.abc import Iterable


LOMIMAIL_DOMAIN = "lomimail.com"
DEFAULT_GRID_ROWS = 64


def normalize_lomimail_local_part(full_name: str) -> str:
    """
    Normalize a full name into a Lomimail address local part.

    Example:
        "Idris Akeem" -> "idrisakeem"
        "John O'Neil" -> "johnoneil"

    Unicode letters and digits are retained after normalization.
    Spaces and punctuation are removed.
    """
    if not isinstance(full_name, str) or not full_name.strip():
        raise ValueError("A non-empty full name is required")

    normalized = unicodedata.normalize("NFKC", full_name).casefold()
    local_part = "".join(
        character
        for character in normalized
        if character.isalnum()
    )

    if not local_part:
        raise ValueError("The name must contain letters or digits")

    return local_part


def generate_lomimail_address(
    full_name: str,
    existing_addresses: Iterable[str] = (),
) -> str:
    """
    Generate a deterministic available Lomimail address.

    The unsuffixed address is preferred. Collisions receive the
    first available numeric suffix: name2, name3, name4, etc.

    Database uniqueness must still be enforced by the caller.
    """
    local_part = normalize_lomimail_local_part(full_name)
    domain = f"@{LOMIMAIL_DOMAIN}"

    existing = {
        address.strip().casefold()
        for address in existing_addresses
        if isinstance(address, str)
    }

    candidate = f"{local_part}{domain}"
    if candidate.casefold() not in existing:
        return candidate

    suffix = 2
    while True:
        candidate = f"{local_part}{suffix}{domain}"
        if candidate.casefold() not in existing:
            return candidate
        suffix += 1



def normalize_phone_uid(phone: str) -> str:
    """
    Normalize a complete international phone number to + followed by digits.

    Accepts harmless formatting such as spaces, hyphens, and parentheses.
    The country calling code must be present; local numbers beginning with
    zero are rejected rather than guessed.

    This validates a basic E.164-compatible shape, not whether the number
    is assigned, reachable, or owned by the caller.
    """
    if not isinstance(phone, str) or not phone.strip():
        raise ValueError("An international phone number is required")

    value = phone.strip()

    # Permit only a leading plus, ASCII digits, and common formatting marks.
    if value.startswith("+"):
        body = value[1:]
    else:
        body = value

    if not body or any(ch not in "0123456789 ()-." for ch in body):
        raise ValueError("Phone number contains unsupported characters")

    digits = "".join(ch for ch in body if ch in "0123456789")

    if not 8 <= len(digits) <= 15:
        raise ValueError("International phone number must contain 8 to 15 digits")

    if digits.startswith("0"):
        raise ValueError(
            "Use the full international number including its country calling code"
        )

    return "+" + digits


def calculate_uid_digit_sum(phone_uid: str) -> int:
    """
    Sum the decimal digits of the phone-derived uID.

    The country calling code is retained in the input and therefore
    contributes to the sum. A leading '+' contributes no digit.
    """
    if not isinstance(phone_uid, str) or not phone_uid.strip():
        raise ValueError("A phone-derived uID is required")

    digits = "".join(
        character
        for character in phone_uid
        if character in "0123456789"
    )

    if not digits:
        raise ValueError("The uID must contain decimal digits")

    return sum(int(digit) for digit in digits)


def calculate_startrow(
    full_name: str,
    phone_uid: str,
    rows: int = DEFAULT_GRID_ROWS,
) -> int:
    """
    Calculate Lomimail's starting row.

    L = length of the normalized name component, before any
        collision-resolution suffix is applied.
    S = sum of the decimal digits of the phone-derived uID.

    Startrow = ((L + S - 1) % rows) + 1
    """
    if not isinstance(rows, int) or isinstance(rows, bool) or rows < 1:
        raise ValueError("Grid row count must be a positive integer")

    L = len(normalize_lomimail_local_part(full_name))
    S = calculate_uid_digit_sum(phone_uid)

    return ((L + S - 1) % rows) + 1


def calculate_lomimail_placement(
    full_name: str,
    phone_uid: str,
    rows: int = DEFAULT_GRID_ROWS,
) -> dict:
    """Return the identity inputs and calculated Lomimail Startrow."""
    L = len(normalize_lomimail_local_part(full_name))
    S = calculate_uid_digit_sum(phone_uid)

    if not isinstance(rows, int) or isinstance(rows, bool) or rows < 1:
        raise ValueError("Grid row count must be a positive integer")

    return {
        "L": L,
        "S": S,
        "start_row": ((L + S - 1) % rows) + 1,
    }
