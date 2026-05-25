import random

# ═══════════════════════════════════════════════════════════════
#  FALLBACK PHRASES
# ═══════════════════════════════════════════════════════════════
#
#  These phrases are used when:
#  1. No AI provider is configured (offline mode)
#  2. The AI provider fails to respond
#  3. The user selected "Frases prontas" as provider
#
#  Each list is a category. The app picks a random entry.
#  Add as many as you want — more variety is better!
#
#  The category names are CASED EXACTLY as shown below
#  (they match the constants referenced by the engine).
#
# ═══════════════════════════════════════════════════════════════

# Shown when the pet first appears
GREETING = [
    "Ola! Como voce esta?",
    "Oieee!",
]

# Follow‑up when the user asks how you are
HOW_ARE_YOU = [
    "Como voce esta?",
    "Tudo bem?",
]

# Reply when user says they're good
RETURN_GOOD = [
    "Que bom!",
    "Feliz em saber!",
]

# Reply when user says they're bad
RETURN_BAD = [
    "Ah, que pena...",
    "Melhoras!",
]

# Reply to "thank you" / "obrigado"
THANKS = [
    "De nada!",
    "Por nada!",
]

# Reply to goodbye
BYE = [
    "Tchau!",
    "Ate logo!",
]

# Catch‑all when nothing else matched
UNKNOWN = [
    "Nao entendi...",
    "Hmm, nao sei o que dizer...",
]

# Alarm phrases (spoken when alarm fires)
ALARM_PHRASES = [
    "Hora do alarme!",
    "Acordaaa!",
]

# Random thinking prefixes (shown while waiting for AI)
THINKING_PREFIXES = [
    "Hmm...",
    "Deixa eu ver...",
]

# Continuation prompts (rarely used)
CONTINUATIONS = [
    "Continue...",
    "E entao?",
]


# ═══════════════════════════════════════════════════════════════
#  KEYWORD MATCHING
# ═══════════════════════════════════════════════════════════════
#
#  CATEGORY_KEYWORDS maps user message keywords to phrase
#  categories. When the user's message contains ANY keyword
#  from a category, a random phrase from that category is
#  returned as the response.
#
#  Example: user says "ola tudo bem?" → matches "greeting"
#  and "how_are_you" → picks a random phrase from the first
#  match (greeting).
#
#  Keywords are checked IN ORDER. The first match wins.
#
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
    """Return a random phrase from the given category list.
    
    category — name of the list variable (e.g. "GREETING")
    default  — fallback text if the list is empty or missing
    """
    lst = globals().get(category, [])
    return random.choice(lst) if lst else default


def get_fallback(message, history=None):
    """Match a user message against CATEGORY_KEYWORDS.
    
    Returns a random phrase from the first matching category,
    or the UNKNOWN fallback if nothing matched.
    """
    msg = message.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return pick(category)
    return pick("unknown", "Nao entendi...")
