"""
LOMINII Language Registry

Registers supported languages for the
Dictionary Engine.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Language:

    code: str

    name: str

    native_name: str

    rtl: bool = False


LANGUAGES = {

    "en": Language(
        "en",
        "English",
        "English",
    ),

    "fr": Language(
        "fr",
        "French",
        "Français",
    ),

    "de": Language(
        "de",
        "German",
        "Deutsch",
    ),

    "ar": Language(
        "ar",
        "Arabic",
        "العربية",
        rtl=True,
    ),

    "yo": Language(
        "yo",
        "Yoruba",
        "Yorùbá",
    ),

    "ig": Language(
        "ig",
        "Igbo",
        "Igbo",
    ),

    "ha": Language(
        "ha",
        "Hausa",
        "Hausa",
    ),

    "zh": Language(
        "zh",
        "Chinese",
        "中文",
    ),
}