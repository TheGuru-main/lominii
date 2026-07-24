from collections import defaultdict

from .models import DictionaryEntry
from .language import LANGUAGES

class DictionaryEngine:
    """
    Universal Dictionary Engine.

    Used by:

    • Search
    • AI
    • EDU
    • Maps
    • BubbleJumbo
    • Related Search
    """

    def __init__(self):

        self.entries = {}

        self.languages = defaultdict(dict)

        self.domains = defaultdict(dict)

        self.entries = {}

        # Language index
        self.languages = defaultdict(dict)

        # Domain index
        self.domains = defaultdict(dict)

        # Alias index
        self.aliases = defaultdict(dict)

        # Category index
        self.categories = defaultdict(dict)

        # Tag index
        self.tags = defaultdict(dict)

        # Phrase index
        self.phrases = defaultdict(dict)

        # Abbreviation index
        self.abbreviations = defaultdict(dict)

    def register(
        self,
        entry: DictionaryEntry,
    ):

        key = (
            entry.language.lower(),
            entry.word.lower(),
        )

        self.entries[key] = entry

        self.languages[
            entry.language.lower()
        ][entry.word.lower()] = entry

        for domain in entry.domains:

            self.domains[
                domain.lower()
            ][entry.word.lower()] = entry

    def lookup(
        self,
        word: str,
        language: str = "en",
    ):

        return self.entries.get(
            (
                language.lower(),
                word.lower(),
            )
        )

    def exists(
        self,
        word: str,
        language: str = "en",
    ) -> bool:

        return self.lookup(
            word,
            language,
        ) is not None

    def synonyms(
        self,
        word: str,
        language: str = "en",
    ) -> list[str]:

        entry = self.lookup(word, language)

        if entry is None:
            return []

        return entry.synonyms

    def related(
        self,
        word: str,
        language: str = "en",
    ) -> list[str]:

        entry = self.lookup(word, language)

        if entry is None:
            return []

        return entry.related

    def translations(
        self,
        word: str,
        language: str = "en",
    ) -> dict:

        entry = self.lookup(word, language)

        if entry is None:
            return {}

        return entry.translations

    def supported_languages(self):

        return LANGUAGES

    def is_supported_language(
        self,
        language: str,
    ) -> bool:

        return language.lower() in LANGUAGES