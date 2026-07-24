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

        # Primary index
        self.entries[key] = entry

        # Language index
        self.languages[
        entry.language.lower()
        ][entry.word.lower()] = entry

        # Domain index
        for domain in entry.domains:

            self.domains[
                domain.lower()
            ][entry.word.lower()] = entry

        # Alias index
        for alias in entry.aliases:

        self.aliases[
            entry.language.lower()
        ][alias.lower()] = entry

        # Category index
        for category in entry.categories:

            self.categories[
                category.lower()
            ][entry.word.lower()] = entry

        # Tag index
        for tag in entry.tags:

        self.tags[
            tag.lower()
        ][entry.word.lower()] = entry

        # Phrase index
        for phrase in entry.phrases:

            self.phrases[
                entry.language.lower()
            ][phrase.lower()] = entry

        # Abbreviation index
        for abbreviation in entry.abbreviations:

            self.abbreviations[
                entry.language.lower()
            ][abbreviation.lower()] = entry

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