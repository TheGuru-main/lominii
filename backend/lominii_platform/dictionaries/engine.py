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

        word = entry.word.lower()
        language = entry.language.lower()

        key = (
            language,
            word,
        )

        # ------------------------------------------------
        # Main entry
        # ------------------------------------------------

        self.entries[key] = entry

        self.languages[language][word] = entry

        # ------------------------------------------------
        # Domains
        # ------------------------------------------------

        for domain in entry.domains:

            self.domains[
                domain.lower()
            ][word] = entry

        # ------------------------------------------------
        # Aliases
        # ------------------------------------------------

        for alias in entry.aliases:

            self.aliases[
                language
            ][alias.lower()] = entry

        # ------------------------------------------------
        # Categories
        # ------------------------------------------------

        for category in entry.categories:

            self.categories[
                category.lower()
            ][word] = entry

        # ------------------------------------------------
        # Tags
        # ------------------------------------------------

        for tag in entry.tags:

            self.tags[
                tag.lower()
            ][word] = entry

        # ------------------------------------------------
        # Phrases
        # ------------------------------------------------

        for phrase in entry.phrases:

            self.phrases[
                language
            ][phrase.lower()] = entry

        # ------------------------------------------------
        # Abbreviations
        # ------------------------------------------------

        for abbreviation in entry.abbreviations:

            self.abbreviations[
                language
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
        language: str = "en", ) -> list[str]:
        entry = self.lookup(word, language)

        if entry is None:
            return []

        return entry.related

    def translations(
        self,
        word: str,
        language: str = "en", ) -> dict:
        entry = self.lookup(word, language)

        if entry is None:
            return {}

        return entry.translations

    def alias(
        self,
        word: str,
        language: str = "en", ):
        return self.aliases[
            language.lower()
        ].get(
        word.lower() )

    def category(
        self,
        category: str, ):
        return list(

            self.categories[
                category.lower()
            ].values() )

    def tag(
        self,
        tag: str,
    ):
        return list(
            self.tags[
                tag.lower()
            ].values()
        )

    def phrase(
        self,
        phrase: str,
        language: str = "en", ):

        return self.phrases[
            language.lower()
        ].get(
            phrase.lower() )

    def abbreviation(
        self,
        abbreviation: str,
        language: str = "en", ):

        return self.abbreviations[
            language.lower()
        ].get(
            abbreviation.lower() )

    def resolve(
        self,
        text: str,
        language: str = "en", ):

        """
        Resolve any dictionary object.

        Order:

        1. Word
        2. Alias
        3. Phrase
        4. Abbreviation
 
        Returns DictionaryEntry or None.
        """

        text = text.lower()

        entry = self.lookup(
            text,
            language, )

        if entry:
            return entry

        entry = self.alias(
            text,
            language, )

        if entry:
            return entry

        entry = self.phrase(
            text,
            language, )

        if entry:
            return entry

        entry = self.abbreviation(
            text,
            language, )

        return entry

    def suggestions(
        self,
        text: str,
        language: str = "en",
    ) -> list[str]:
        """Return up to ten matching words from a language dictionary."""
        query = (text or "").strip().casefold()

        if not query:
            return []

        language = (language or "en").strip().lower()
        entries = self.languages.get(language, {})

        prefix_matches = []
        substring_matches = []

        for word in entries:
            candidate = word.casefold()

            if candidate.startswith(query):
                prefix_matches.append(word)
            elif query in candidate:
                substring_matches.append(word)

        prefix_matches.sort(key=str.casefold)
        substring_matches.sort(key=str.casefold)

        return (prefix_matches + substring_matches)[:10]

    def translate(
        self,
        word: str,
        target_language: str,
        source_language: str = "en",
    ) -> list[str]:
        """Return stored translations for a word in the target language."""
        word = (word or "").strip()
        source_language = (source_language or "en").strip().lower()
        target_language = (target_language or "").strip().lower()

        if not word or not target_language:
            return []

        entry = self.lookup(word, source_language)

        if entry is None:
            entry = self.resolve(word, source_language)

        if entry is None:
            return []

        translations = entry.translations or {}
        result = translations.get(target_language, [])

        if isinstance(result, str):
            return [result] if result else []

        return list(result) if result else []

    def supported_languages(self):

        return LANGUAGES

    def is_supported_language(
        self,
        language: str,
    ) -> bool:

        return language.lower() in LANGUAGES