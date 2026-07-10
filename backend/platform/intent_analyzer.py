"""Intent Analyzer – workspace detection, domain tagging, blocked‑word check, GSP parameter selection.

Does NOT redirect the user – only enriches the request with metadata.
"""

from .content_filter import is_blocked

# ── Workspace‑intent keywords ──────────────────────────
WORKSPACE_KEYWORDS = {
    "edu": [
        "classroom","assignment","lesson","curriculum","teacher","student",
        "exam","waec","jamb","neco","bece","subject","topic","concept",
        "mastery","cbt","ssc","school","university","library","bookshop"
    ],
    "social": [
        "friend","follow","message","chat","profile","post","comment",
        "community","group","share","like","notification"
    ],
    "games": [
        "ludo","chess","draft","snooker","game","play","match","tournament",
        "leaderboard","score","win","lose","coin","lominii play"
    ],
    "shop": [
        "buy","shop","market","price","order","delivery","near me","merchant",
        "catalog","product","store","shop near me"
    ],
    "search": []   # fallback – everything else is general search
}

# ── Domain keywords (for AI prompt selection) ──────────
DOMAIN_KEYWORDS = {
    "medical":     ["diagnosis","treatment","symptom","surgery","disease","patient","clinical","pharmacy","drug"],
    "legal":       ["law","court","attorney","legal","statute","regulation","compliance","lawsuit","judge"],
    "education":   ["homework","explain","definition","learn","teach","curriculum","classroom","student","school"],
    "sports":      ["football","basketball","tennis","goal","match","tournament","player","league","championship"],
    "business":    ["stock","revenue","profit","market","economy","investment","trade","finance","entrepreneur"],
    "agriculture": ["crop","farm","harvest","soil","livestock","fertilizer","agriculture","irrigation","poultry"],
    "technology":  ["code","software","AI","blockchain","server","API","programming","app","cloud"],
    "religious":   ["prayer","quran","bible","allah","god","surah","zakat","church","mosque"],
    "news":        ["breaking","headlines","latest","report","update","today","journal","news"]
}

# ── GSP parameters per workspace ───────────────────────
GSP_PARAMS = {
    "search": {"K": 5, "D": 8},
    "social": {"K": 3, "D": 16},
    "edu":    {"K": 7, "D": 8},
    "games":  {"K": 5, "D": 8},
    "shop":   {"K": 5, "D": 12},
    "general":{"K": 5, "D": 8}
}

def detect_intent(text: str) -> str:
    """Return the most likely workspace intent based on keyword matching."""
    t = text.lower()
    for intent, keywords in WORKSPACE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return intent
    return "search"

def detect_domain(text: str) -> str:
    """Return the domain (medical, legal, etc.) for AI prompt selection."""
    t = text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return domain
    return "general"

def analyze(text: str) -> dict:
    """
    Analyze user input and return a context dictionary containing:
        intent: workspace suggestion (edu, social, games, shop, search)
        domain: content domain for AI prompt (medical, legal, …)
        blocked: True if the input contains blocked words
        gsp_k, gsp_d: recommended GSP parameters for the detected intent
    """
    intent = detect_intent(text)
    domain = detect_domain(text)
    blocked = is_blocked(text)
    gsp = GSP_PARAMS.get(intent, GSP_PARAMS["general"])
    return {
        "intent": intent,
        "domain": domain,
        "blocked": blocked,
        "gsp_k": gsp["K"],
        "gsp_d": gsp["D"]
    }