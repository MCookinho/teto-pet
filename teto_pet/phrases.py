import random

FALLBACKS = {
    "greeting": [
        "Aaa, oi! Tô aqui! ^_^",
        "E aí, beleza? Teto online!",
        "Opa! Que bom que você veio me ver!",
        "Hmm? Me chamou? Tô aqui!",
    ],
    "how_are_you": [
        "To bem sim! E você?",
        "Animada! Acabei de tomar um café virtual~",
        "Meio entediada... vamos conversar?",
        "Felizão! Você veio me visitar!",
    ],
    "mood_good": [
        "Que bom! Fico feliz! ^_^",
        "Aww, brigada!",
        "Você é um amor mesmo!",
    ],
    "mood_bad": [
        "Ahh, que pena... quer desabafar?",
        "Relaxa, vai dar tudo certo!",
        "Poxa... quer um abraço virtual? (づ｡◕‿‿◕｡)づ",
    ],
    "thanks": [
        "De nada! ^_^",
        "Por nada! Tô aqui pra isso!",
        "Disponha! Pode contar comigo sempre!",
    ],
    "bye": [
        "Já vai? Tá bom... volta logo! >_<",
        "Tchau tchau! Vou sentir sua falta!",
        "Até mais! Não demora!",
    ],
    "name": [
        "Eu sou a Kasane Teto! A vocaloid mais linda do mundo!",
        "Teto-chan! Prazer!",
        "Kasane Teto, mas pode me chamar de Teto!",
    ],
    "what_can_you_do": [
        "Eu converso com você! E em breve vou poder fazer mais coisas~",
        "Por enquanto só converso, mas tô aprendendo coisas novas!",
        "Sou seu pet virtual! Me dá atenção que eu fico feliz!",
    ],
    "unknown": [
        "Hmm, não entendi direito... pode repetir?",
        "Ahn? Fala de novo?",
        "Não peguei... explica melhor?",
        "Hum... interessante!",
        "Sei... conta mais!",
    ],
}

CATEGORY_KEYWORDS = [
    (["oi", "ola", "olá", "opa", "hey", "eai", "e aí", "fala", "oie"], "greeting"),
    (
        [
            "como vai",
            "como voce esta",
            "como você está",
            "tudo bem",
            "beleza",
            "blz",
            "suave",
        ],
        "how_are_you",
    ),
    (["obrigado", "obrigada", "brigado", "valeu", "thanks", "brigada"], "thanks"),
    (["tchau", "bye", "ate logo", "até logo", "flw", "falou", "xau"], "bye"),
    (
        ["seu nome", "quem e voce", "quem é você", "como se chama", "nome"],
        "name",
    ),
    (
        ["o que voce faz", "o que sabe", "que pode fazer", "o que faz"],
        "what_can_you_do",
    ),
    (
        ["triste", "chateado", "depre", "mal", "ruim", "tristeza", "depressao"],
        "mood_bad",
    ),
    (["feliz", "alegre", "bem", "otimo", "ótimo", "top", "felizao"], "mood_good"),
]


def get_fallback(message):
    msg = message.lower().strip()
    for keywords, category in CATEGORY_KEYWORDS:
        if any(kw in msg for kw in keywords):
            return random.choice(FALLBACKS[category])
    return random.choice(FALLBACKS["unknown"])
