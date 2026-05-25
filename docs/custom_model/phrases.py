import random

# ── Phrase Lists ───────────────────────────────────────────
# Each list is a category of phrases your pet can say.
# Add as many phrases as you want per category.
# Used as fallback when no AI provider is configured.

GREETING = [
    "Ola! Como voce esta?",
    "Oieee!",
]

HOW_ARE_YOU = [
    "Como voce esta?",
    "Tudo bem?",
]

RETURN_GOOD = [
    "Que bom!",
    "Feliz em saber!",
]

RETURN_BAD = [
    "Ah, que pena...",
    "Melhoras!",
]

THANKS = [
    "De nada!",
    "Por nada!",
]

BYE = [
    "Tchau!",
    "Ate logo!",
]

UNKNOWN = [
    "Nao entendi...",
    "Hmm, nao sei o que dizer...",
]

# Alarm and thinking phrases
ALARM_PHRASES = [
    "Hora do alarme!",
    "Acordaaa!",
]

THINKING_PREFIXES = [
    "Hmm...",
    "Deixa eu ver...",
]

CONTINUATIONS = [
    "Continue...",
    "E entao?",
]

# ── Keyword Matching ──────────────────────────────────────
# Map user message keywords to phrase categories.
# When a user's message contains any keyword, the
# corresponding category is used as a response.
CATEGORY_KEYWORDS = {
    "greeting": ["ola", "oie", "oi", "hey", "fala a", "e ai"],
    "how_are_you": [
        "como voce esta", "tudo bem", "como vai",
        "como voce ta", "beleza",
    ],
    "return_good": ["bem", "otimo", "maravilha", "feliz"],
    "return_bad": ["mal", "triste", "cansado", "ruim"],
    "thanks": [
        "obrigado", "valeu", "brigado", "thanks",
        "muito obrigado",
    ],
    "bye": [
        "tchau", "ate logo", "ate mais", "adeus",
        "ate amanha", "falou",
    ],
}


def pick(category, default=""):
    """Return a random phrase from the given category."""
    lst = globals().get(category, [])
    return random.choice(lst) if lst else default


def get_fallback(message, history):
    """Match a user message against keywords and return a response."""
    msg = message.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return pick(category)
    return pick("unknown", "Nao entendi...")
