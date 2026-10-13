from dataclasses import dataclass, field


@dataclass(slots=True)
class DictionaryEntry:
    """
    Universal dictionary entry used by
    Search, AI, EDU, Maps and BubbleJumbo.
    """

    word: str

    language: str

    definitions: list[str] = field(default_factory=list)

    synonyms: list[str] = field(default_factory=list)

    related: list[str] = field(default_factory=list)

    translations: dict[str, list[str]] = field(default_factory=dict)

    domains: list[str] = field(default_factory=list)

    # New indexes
    aliases: list[str] = field(default_factory=list)

    categories: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)

    phrases: list[str] = field(default_factory=list)

    abbreviations: list[str] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)