"""
LOMINII Language Registry.

Provides language-specific keyboard layouts independently of
the GSP placement grid and tokenizer recognition chain.
"""

from .english import KEYBOARD as ENGLISH
from .french import KEYBOARD as FRENCH
from .german import KEYBOARD as GERMAN


KEYMAPS = {
    "en": ENGLISH,
    "fr": FRENCH,
    "de": GERMAN,
}


def get_keyboard(language: str = "en") -> list[str]:
    """
    Return the keyboard layout for a language.

    Unsupported languages fall back to English.
    """
    language = (language or "en").lower().strip()
    return KEYMAPS.get(language, KEYMAPS["en"])


def register(language: str, keyboard: list[str]) -> None:
    """
    Register or replace a language keyboard layout.
    """
    language = language.lower().strip()

    if not language:
        raise ValueError("Language code cannot be empty")

    if not isinstance(keyboard, list) or not all(
        isinstance(row, str) for row in keyboard
    ):
        raise TypeError("Keyboard must be a list of strings")

    KEYMAPS[language] = keyboard
