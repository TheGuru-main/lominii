"""Content Filter (Platform Layer)"""

# Words that are completely blocked (no search results, no AI summary)
BLOCKED = {
    # Adult / explicit
    "porn", "gay", "lesbian", "nude", "masturbation", "chartubate",
    "sexy", "xxx", "adult",
    # Gambling / betting (block AI explanation, not the search itself)
    "bet", "bet9ja", "sportybet", "nairabet", "betway",
    # Offensive / irrelevant
    "crazy", "mad",
    # Additional explicit terms
    "sex", "penis", "vagina", "fuck", "dick", "pussy",
    "escort", "stripper", "onlyfans"
}

# Words where AI explanation is blocked, but search results may still show
AI_BLOCKED = {
    "bet", "bet9ja", "sportybet", "nairabet", "betway",
    "gay", "lesbian", "nude", "masturbation", "chartubate",
    "sexy", "sex", "crazy", "mad"
}

def is_blocked(text: str) -> bool:
    """Return True if the text contains any completely blocked word."""
    lower = text.lower()
    return any(word in lower for word in BLOCKED)

def is_ai_blocked(text: str) -> bool:
    """Return True if AI explanation should be suppressed for this text."""
    lower = text.lower()
    return any(word in lower for word in AI_BLOCKED)