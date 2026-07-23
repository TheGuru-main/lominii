from dataclasses import dataclass, field


@dataclass(slots=True)
class DictionaryEntry:
    """
    Universal dictionary entry.

    Every language and domain dictionary
    uses the same structure.
    """

    word: str

    language: str

    translations: dict[str, list[str]] = field(default_factory=dict)

    synonyms: list[str] = field(default_factory=list)

    related: list[str] = field(default_factory=list)

    domains: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)