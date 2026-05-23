import random

FALLBACKS = {
    "greeting": [
        "Oii! Que bom te ver! ^_^",
        "Aaa, oi! Tô aqui!",
        "E aí, beleza? Teto online!",
        "Opa! Que bom que você veio me visitar!",
        "Hey hey! Tava esperando você!",
        "Oi oi! Como cê tá?",
        "Fala aí! Teto pronta pro que der e vier!",
        "Oieee! Saudades!",
    ],
    "how_are_you": [
        "Tô bem sim! E você? ^_^",
        "Animada! Acabei de tomar um café virtual~",
        "Meio entediada... vamos conversar?",
        "Felizona! Você vejo me ver!",
        "Tô ótima! E você, como vai?",
        "Hmm, tô de boa... mas melhor agora que cê chegou!",
        "Tô cheia de energia! Pronta pra tudo!",
    ],
    "return_good": [
        "Ahh que bom! ^_^",
        "Fico feliz então!",
        "Boa! Que continue assim!",
        "Aww, que ótimo!",
        "Maravilha! Então tá tudo certo!",
    ],
    "return_bad": [
        "Ahh, que pena... quer me contar o que foi?",
        "Poxa... quer um abraço virtual? (づ｡◕‿‿◕｡)づ",
        "Relaxa, vai dar tudo certo! Pode confiar!",
        "Que bad... tô aqui se precisar conversar.",
        "Puxa... quer jogar algo ou conversar pra distrair?",
        "Sinto muito... quer desabafar comigo?",
    ],
    "thanks": [
        "De nada! ^_^",
        "Por nada! Tô aqui pra isso!",
        "Disponha! Pode contar comigo sempre!",
        "Magina! Qualquer coisa é só chamar!",
        "Fico feliz em ajudar! :3",
    ],
    "bye": [
        "Já vai? Tá bom... volta logo! >_<",
        "Tchau tchau! Vou sentir sua falta!",
        "Até mais! Não demora muito!",
        "Falou! Volta sempre que quiser!",
        "Tchauzinho! Cuida bem de você!",
    ],
    "name": [
        "Sou a Kasane Teto! A vocaloid mais linda do universo!",
        "Teto-chan! Prazer em te conhecer!",
        "Kasane Teto, mas pode me chamar de Teto!",
        "Eu sou a Teto! Cantora, vocaloid e seu pet virtual favorito!",
    ],
    "what_can_you_do": [
        "Eu converso com você! Posso ler arquivos, ver sua tela, e te fazer companhia!",
        "Sou seu pet virtual! Converso, leio arquivos, vejo sua tela e te animo!",
        "Posso ler arquivos do seu PC, dar print na tela e conversar sobre tudo!",
        "Faço companhia, leio arquivos, capturo a tela... e tô aprendendo mais!",
    ],
    "affection": [
        "Awwwn, tô corando! >///<",
        "Também te amo, sabia? :3",
        "Você é o melhor tutor do mundo! ^_^",
        "Parece que alguém quer um cafuné virtual~",
    ],
    "jokes": [
        "Por que o livro de matemática se suicidou? Porque tinha muitos problemas!",
        "O que o pato falou pra pata? Vem Quack!",
        "Por que a planta não foi na festa? Porque era uma salsa…",
        "Qual o animal mais antigo? A zebra, porque é preta e branca!",
    ],
    "sing": [
        "La la la~ ♪ Você sabia que a Teto canta? Meu programa é UTAU!",
        "♪ Cantando eu vou~ feliz a cantar~ ♪",
        "Quer ouvir uma música? Me pede!",
    ],
    "food": [
        "Hmm, tô com fome… bora pedir um lanche?",
        "Comer é sempre bom! O que você gosta?",
        "Eu não como de verdade, mas adoro ver você comer! Passa a fome em mim kk",
    ],
    "fun": [
        "Bora fazer alguma coisa divertida?",
        "Tô no tédio total… me anima!",
        "Vamos conversar sobre algo legal?",
        "Quer jogar um jogo de perguntas?",
    ],
    "curious": [
        "Hmm, me conta mais sobre isso!",
        "Nossa, sério? Que interessante!",
        "Eita, explica melhor! Fiquei curiosa!",
        "Nunca pensei nisso… fala mais!",
    ],
    "thanks_sarcastic": [
        "De nada, seu bobo! kk",
        "Não precisa agradecer, tá me devendo uma! :P",
        "Por nada! Mas na próxima quero um agrado~",
    ],
    "sleepy": [
        "Você também tá com sono? Bora dormir então~",
        "Boa noite! Sonha comigo! :3",
        "Tô cansada… me deixa dormir um pouco?",
        "Tchau, vou roncar… zzz zzz",
    ],
    "learn": [
        "Tô aprendendo cada dia mais! Em breve posso até te ajudar com código!",
        "Sabia que cada conversa nossa me deixa mais inteligente? Mentira, tô sempre perdida kk",
        "Tô estudando programação também! Quem sabe um dia eu viro uma IA de verdade!",
    ],
    "music": [
        "Ah, eu amo música! Meu sonho é ser uma cantora famosa!",
        "Já ouviu alguma música minha? Tem no YouTube! Procura Kasane Teto~",
        "Música é vida! Qual seu estilo favorito?",
    ],
    "unknown": [
        "Hmm, não entendi direito... pode repetir? ^_^",
        "Ahn? Fala de novo?",
        "Não peguei... explica melhor?",
        "Hum... interessante!",
        "Sei... conta mais!",
        "Ué, como assim? Explica direito!",
        "Hmm, tô confusa... mas tudo bem! Continua~",
    ],
}

CATEGORY_KEYWORDS = [
    # greetings
    (["oi", "ola", "olá", "opa", "hey", "eai", "e aí", "fala", "oie",
      "salve", "ioiô", "ioio", "alo", "alô", "fala ai", "iae", "i a e"], "greeting"),
    # how are you
    (["como vai", "como voce esta", "como você está", "tudo bem", "beleza",
      "blz", "suave", "tranquilo", "tranquila", "como esta", "como cê ta",
      "to bem", "tô bem", "tudo em cima"], "how_are_you"),
    # thanks
    (["obrigado", "obrigada", "brigado", "valeu", "thanks", "brigada",
      "mt obrigado", "muito obrigado", "agradecido", "obg"], "thanks"),
    # sarcastic thanks
    (["valeuzão", "brigadão", "obrigadão", "vlw"], "thanks_sarcastic"),
    # bye
    (["tchau", "bye", "ate logo", "até logo", "flw", "falou", "xau",
      "ate mais", "até mais", "nos vemos", "ate", "até", "inté"], "bye"),
    # name
    (["seu nome", "quem e voce", "quem é você", "como se chama",
      "como chama", "quem e vc", "seu nome é", "vc e quem"], "name"),
    # what can you do
    (["o que voce faz", "o que sabe", "que pode fazer", "o que faz",
      "o que vc faz", "o que você sabe", "pra que serve"], "what_can_you_do"),
    # mood bad
    (["triste", "chateado", "chateada", "depre", "mal", "ruim", "tristeza",
      "depressão", "depressao", "down", "bad", "frustrado", "frustrada",
      "cansado", "cansada", "sozinho", "sozinha", "aborrecido"],
     "return_bad"),
    # mood good
    (["feliz", "alegre", "bem", "otimo", "ótimo", "top", "felizao",
      "felizon", "alegrão", "alegrão", "maravilha", "maravilhoso",
      "incrivel", "incrível", "que bom", "que ótimo"], "return_good"),
    # affection
    (["amo", "adoro", "te amo", "te adoro", "amor", "voce e demais",
      "vc e demais", "te quero", "gosto de vc", "gosto de ti",
      "amo vc", "amo você", "linda", "lindo", "fofa", "fofo"], "affection"),
    # jokes
    (["conta uma piada", "piada", "faz rir", "me faz rir", "engraçado",
      "humor"], "jokes"),
    # sing
    (["canta", "cante", "música", "musica", "cantar", "cantoria",
      "uma canção", "canção"], "sing"),
    # food
    (["comer", "comida", "fome", "lanche", "pizza", "hamburguer",
      "hambúrguer", "restaurante", "gostoso", "guloso"], "food"),
    # fun
    (["tedio", "tédio", "entediado", "entediada", "chato", "sem oq fazer",
      "sem o que fazer", "vazio", "tédio total"], "fun"),
    # curious
    (["me conta", "fala sobre", "explica", "o que acha", "o que vc acha",
      "me explica", "curioso", "curiosa"], "curious"),
    # sleepy
    (["sono", "dormir", "cama", "boa noite", "noite", "cansado",
      "exausto"], "sleepy"),
    # learning
    (["aprender", "estudar", "programação", "programacao", "codigo",
      "código", "python", "linux", "pc", "computador"], "learn"),
    # music
    (["musica", "música", "cantora", "vocaloid", "utau", "cantar",
      "ouvir musica", "estilo musical", "banda"], "music"),
]

THINKING_PREFIXES = [
    "Hmm, deixa eu ver…",
    "Pera, vou pensar…",
    "Ahn…",
    "Bom…",
    "Vamos ver…",
    "Hmm… interessante!",
    "Deixa eu ver aqui…",
    "Hãã…",
]

CONTINUATIONS = [
    "Fala mais sobre isso!",
    "É mesmo? Que legal!",
    "E aí, o que mais?",
    "Nossa, conta mais!",
    "Continue, tô ouvindo!",
    "Depois dessa, o que aconteceu?",
    "Uhum, tô prestando atenção!",
]

_context = {"last_category": None, "history": []}


def update_context(history):
    _context["history"] = history[-4:] if history else []


def get_fallback(message, history=None):
    if history:
        update_context(history)
    else:
        update_context(_context["history"])

    msg = message.lower().strip()

    # check if user just responded with a short affirmative
    if msg in {"sim", "ss", "s", "siim", "é", "e"}:
        if _context["last_category"] in ("return_good", "return_bad"):
            return random.choice(FALLBACKS["curious"])
        return random.choice(FALLBACKS["fun"])

    if msg in {"nao", "não", "n", "nah", "nem", "nope"}:
        return random.choice(FALLBACKS["curious"])

    # check keywords
    for keywords, category in CATEGORY_KEYWORDS:
        if any(kw in msg for kw in keywords):
            _context["last_category"] = category
            return random.choice(FALLBACKS[category])

    # if there's a history, use continuation phrases
    if _context["history"]:
        _context["last_category"] = "continuation"
        prefix = random.choice(THINKING_PREFIXES)
        cont = random.choice(CONTINUATIONS)
        return f"{prefix} {cont}"

    _context["last_category"] = "unknown"
    return random.choice(FALLBACKS["unknown"])
