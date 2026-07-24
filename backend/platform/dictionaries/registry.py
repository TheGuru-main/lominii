from . import english
from . import french
from . import german


DICTIONARY = {
    english.LANGUAGE: english,
    french.LANGUAGE: french,
    german.LANGUAGE: german,
}


def get_dictionary(language: str):
    """
    Returns the dictionary module for a language.

    Falls back to English.
    """

    return DICTIONARY.get(
        language,
        english,
    )