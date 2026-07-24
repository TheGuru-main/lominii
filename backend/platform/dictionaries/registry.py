from . import english
from . import french
from . import german


LANGUAGE_REGISTRY = {
    english.LANGUAGE: english,
    french.LANGUAGE: french,
    german.LANGUAGE: german,
}


def get_dictionary(language: str):
    """
    Returns the dictionary module for a language.

    Falls back to English.
    """

    return LANGUAGE_REGISTRY.get(
        language,
        english,
    )