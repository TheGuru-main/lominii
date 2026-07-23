from .engine import DictionaryEngine
from .models import DictionaryEntry


dictionary = DictionaryEngine()


dictionary.register(

    DictionaryEntry(

        word="hospital",

        language="en",

        translations={
            "fr": ["hôpital"],
            "de": ["krankenhaus"],
            "ar": ["مستشفى"],
            "yo": ["ilé ìwòsàn"],
        },

        synonyms=[
            "clinic",
            "medical center",
            "health facility",
        ],

        related=[
            "doctor",
            "nurse",
            "medicine",
            "patient",
            "emergency",
        ],

        domains=[
            "medical",
        ],

        tags=[
            "health",
        ],
    )
)