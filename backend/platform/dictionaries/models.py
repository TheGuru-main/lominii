"""
LOMINII Dictionary Basemodel Types

Every language dictionary must follow this structure.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class DictionaryEntry:
    """
    A single dictionary entry.
    """

    word: str

    language: str

    translations: dict[str, list[str]] = field(default_factory=dict)

    synonyms: list[str] = field(default_factory=list)

    aliases: list[str] = field(default_factory=list)

    categories: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)