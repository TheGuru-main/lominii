"""
LOMINII Language Registry
"""

from .english import KEYBOARD as ENGLISH
from .french import KEYBOARD as FRENCH
from .german import KEYBOARD as GERMAN

KEYMAPS = {
    "en": ENGLISH,
    "fr": FRENCH,
    "de": GERMAN,
}


    def get_keyboard(language: str):
        """
        Returns the keyboard layout for a language.

        Falls back to English if unavailable.
        """
        return KEYMAPS.get(language, KEYMAPS["en"])


    def register(language: str, keyboard: list[str]):
        """
        Register a new language keyboard.
        """
        KEYMAPS[language] = keyboard