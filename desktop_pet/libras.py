import re

_ARTICLES = {"o", "a", "os", "as", "um", "uma", "uns", "umas"}
_PREPOSITIONS = {
    "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "para", "pra", "por", "pelo", "pela", "pelos", "pelas", "com",
    "sem", "sob", "sobre", "entre", "ate", "desde",
}
_PRONOUNS = {
    "eu", "tu", "ele", "ela", "nos", "vos", "eles", "elas",
    "me", "te", "se", "lhe", "lhes", "nos", "vos",
    "este", "esta", "esse", "essa", "aquele", "aquela",
}
_VERBS_TO_INFINITIVE = re.compile(
    r"\b(\w+)(?:ndo|do|ndo|mos|ram|r[aoei]s?|v[aoeis]+)\b", re.IGNORECASE
)

# Tempo verbal: simplifica verbos conjugados pro infinitivo
_VERB_CONJUGATIONS = [
    (re.compile(r"\b(\w+)ndo\b", re.IGNORECASE), r"\1"),          # falando -> falar
    (re.compile(r"\b(\w+)mos\b", re.IGNORECASE), r"\1"),           # falamos -> falar
    (re.compile(r"\b(\w+)(?:ram|rao)\b", re.IGNORECASE), r"\1"),   # falaram -> falar
    (re.compile(r"\b(\w+)(?:ria|riam)\b", re.IGNORECASE), r"\1"),  # falaria -> falar
    (re.compile(r"\b(\w+)(?:v[aeo])\b", re.IGNORECASE), r"\1"),    # falava -> falar
    (re.compile(r"\b(\w+)(?:[aeo]s)\b", re.IGNORECASE), r"\1"),    # falas/fales -> falar
]

# Dicionario de sinais comuns (palavra -> sinal em LIBRAS)
_SIGNS = {
    "oi": "OI",
    "ola": "OLA",
    "oie": "OI",
    "tchau": "TCHAU",
    "obrigado": "OBRIGADO",
    "obrigada": "OBRIGADO",
    "por favor": "POR-FAVOR",
    "desculpa": "DESCULPA",
    "desculpe": "DESCULPA",
    "sim": "SIM",
    "nao": "NAO",
    "bem": "BEM",
    "mal": "MAL",
    "triste": "TRISTE",
    "feliz": "FELIZ",
    "bravo": "BRAVO",
    "cansado": "CANSADO",
    "com fome": "FOME",
    "com sede": "SEDE",
    "obrigado": "OBRIGADO",
    "bom dia": "BOM-DIA",
    "boa tarde": "BOA-TARDE",
    "boa noite": "BOA-NOITE",
    "como voce esta": "VOCE COMO-ESTA",
    "tudo bem": "TUDO-BEM",
    "ate logo": "ATE-LOGO",
    "ate mais": "ATE-MAIS",
    "parabens": "PARABENS",
}

# Frases completas (prioridade maxima)
_PHRASES = {
    # Greetings
    "ola como voce esta": "OLA VOCE COMO-ESTA",
    "oii que bom te ver": "OI BOM VER-VOCE",
    "e ai beleza": "EI TUDO-BEM",
    "opa que bom que voce veio": "OPA BOM CHEGAR",
    "hey hey tava esperando voce": "HEY ESPERAR VOCE",
    "fala ai pronta pro que der e vier": "FALA-AI PRONTA TUDO",
    "oieee saudades": "OI SENTIR-FALTA",
    # How are you
    "to bem sim e voce": "BEM SIM VOCE",
    "animada acabei de tomar um cafe virtual": "ANIMADA CAFE VIRTUAL TOMAR",
    "to otima e voce como vai": "OTIMA VOCE COMO-VAI",
    "hmm to de boa mas melhor agora que chegou": "BOA MELHOR AGORA VOCE CHEGAR",
    # Return good
    "ahh que bom": "AH BOM",
    "fico feliz entao": "FELIZ ENTÃO",
    "boa que continue assim": "BOA CONTINUAR ASSIM",
    "maravilha entao ta tudo certo": "MARAVILHA TUDO-CERTO",
    # Return bad
    "ahh que pena quer me contar o que foi": "AH PENA QUERER CONTAR",
    "poxa quer um abraco virtual": "POXA ABRACO VIRTUAL QUERER",
    "relaxa vai dar tudo certo": "RELAXAR TUDO-CERTO VAI",
    # Thanks
    "de nada": "DE-NADA",
    "por nada to aqui pra isso": "NADA AQUI PARA-ISSO",
    "disponha pode contar comigo sempre": "DISPONHA CONTAR COMIGO SEMPRE",
    "fico feliz em ajudar": "FELIZ AJUDAR",
    # Bye
    "ja vai ta bom volta logo": "JA-VAI BOM VOLTAR-LOGO",
    "tchau tchau vou sentir sua falta": "TCHAU SENTIR-FALTA",
    "ate mais nao demora muito": "ATE-MAIS NAO-DEMORAR",
    "tchauzinho cuida bem de voce": "TCHAU CUIDAR VOCE",
    # Alarm
    "hora do alarme": "HORA ALARME",
    "acordaaa": "ACORDAR",
    "alarme desligado": "ALARME DESLIGAR",
    "alarme removido": "ALARME REMOVER",
    "alarme adicionado": "ALARME ADICIONAR",
    # Name
    "sou kasane teto a vocaloid mais linda do universo": "SOU KASANE-TETO VOCALOID LINDA UNIVERSO",
    "teto chan prazer em te conhecer": "TETO PRAZER CONHECER",
    "eu sou teto cantora vocaloid e seu pet virtual favorito": "SOU TETO CANTORA VOCALOID PET VIRTUAL FAVORITO",
    # Misc
    "nao entendi": "NAO-ENTENDER",
    "hmm nao sei o que dizer": "HM NAO-SABER DIZER",
    "continue": "CONTINUAR",
    "e entao": "E-ENTAO",
    # Screen reading / accessibility
    "descreva o que voce ve nesta captura de tela": "DESCREVER VER CAPTURA-TELA",
    "comente sobre o que foi falado neste audio": "COMENTAR FALAR AUDIO",
    # Ollama
    "ollama ligado pronto pra conversar": "OLLAMA LIGAR PRONTO CONVERSAR",
    "nao achei o ollama vou usar frases prontas mesmo": "NAO-ACHAR OLLAMA USAR FRASES",
    # Fish audio
    "fish audio configurado": "FISH-AUDIO CONFIGURAR",
    "nao colou nenhuma chave tenta de novo": "NAO-COLAR CHAVE TENTAR NOVAMENTE",
}


def _apply_rules(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-zà-ÿ0-9\s]", "", text)
    words = text.split()

    # Remove artigos e preposicoes
    words = [w for w in words if w not in _ARTICLES and w not in _PREPOSITIONS]

    # Simplifica verbos (tentativa basica de infinitivo)
    for pattern, replacement in _VERB_CONJUGATIONS:
        words = [pattern.sub(replacement, w) for w in words]

    # Ordem: sujeito + objeto + verbo (SOV) - simplificado
    # Na pratica, apenas remove artigos e inverter negacao
    has_neg = "nao" in words
    if has_neg:
        words.remove("nao")

    # Move negacao pro final
    if has_neg:
        words.append("NAO")

    return " ".join(words)


def translate(text):
    if not text or not text.strip():
        return text

    # Tenta frase completa primeiro
    key = text.lower().strip()
    key = re.sub(r"[^a-zà-ÿ0-9\s]", "", key)
    key = re.sub(r"\s+", " ", key).strip()

    if key in _PHRASES:
        return _PHRASES[key]

    # Tenta match parcial (se a frase contem alguma chave)
    for phrase, gloss in _PHRASES.items():
        if phrase in key or key in phrase:
            return gloss

    # Tenta palavra por palavra
    words = text.split()
    translated = []
    for w in words:
        clean = re.sub(r"[^a-zà-ÿA-ZÀ-ÿ0-9]", "", w).lower()
        if clean in _SIGNS:
            translated.append(_SIGNS[clean])
        else:
            translated.append(clean.upper())

    if translated:
        return " ".join(translated)

    # Fallback: aplica regras gramaticais basicas
    return _apply_rules(text).upper()
