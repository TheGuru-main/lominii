"""
LOMINII Language Registry.

Delegates to keymaps.keyboard, the single source of truth for alphabets,
keyboard rows and the tokenizer.
"""
from . import keyboard as _keyboard
from .keyboard import KEYBOARDS, SUPPORTED_LANGUAGES, get_keyboard

KEYMAPS = {code: list(rows) for code, rows in KEYBOARDS.items()}


def register(language: str, keyboard: list[str]) -> None:
    """Register or replace a keyboard layout (alphabet must exist already)."""
    language = language.lower().strip()
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unknown language: {language!r}")
    if not isinstance(keyboard, list) or not all(isinstance(r, str) for r in keyboard):
        raise TypeError("Keyboard must be a list of strings")
    _keyboard.KEYBOARDS[language] = tuple(keyboard)
    KEYMAPS[language] = keyboard
