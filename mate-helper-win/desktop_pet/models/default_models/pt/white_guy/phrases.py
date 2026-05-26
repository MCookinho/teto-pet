import random
from .model import PET_NAME, PET_SHORT_NAME

FALLBACKS = {
    "greeting": [
        f"{PET_SHORT_NAME} pronto. Qual a demanda?",
        "Sistema operacional carregado. Pode falar.",
        "Inicialização completa. Estou aqui.",
        "Pronto. O que precisa?",
        "Boot finalizado. À disposição.",
    ],
    "how_are_you": [
        "Todos os sistemas operacionais. Tudo dentro do esperado.",
        "100% operacional. E você?",
        "Zero lentidão, zero erros. Tudo fluindo.",
        "Funcionando perfeitamente. Como avalia o desempenho?",
        "Nenhum processo em segundo plano travado. Estou bem, obrigado.",
    ],
    "return_good": [
        "Bom saber. Mantenha o ritmo.",
        "Ótimo. Diagnóstico positivo confirmado.",
        "Perfeito. Nada a reportar.",
        "Nota 10. Segue o plano.",
        "Excelente. Continue assim.",
    ],
    "return_bad": [
        "Identificou um problema? Me explique que eu ajudo a resolver.",
        "Queda de desempenho detectada. Quer otimizar algo?",
        "Pode falar. Se for algo técnico, resolvo.",
        "Relate o erro que eu cuido disso.",
        "Engatou? Me passa mais detalhes que a gente desengata.",
    ],
    "thanks": [
        "Disponha. Pra isso que existo.",
        "Resolvido. Qual o próximo comando?",
        "Tamo junto. Qualquer coisa é só chamar.",
        "Não precisa agradecer. Faz parte do serviço.",
        "Sempre que precisar, a gente resolve.",
    ],
    "bye": [
        "Desligando sessão. Até a próxima.",
        "Fechando. Se precisar, é só reabrir o processo.",
        "Até logo. Estou em standby.",
        "Sistema em pausa. Me chama quando voltar.",
        "Encerrando. Lembre-se: estou sempre rodando em segundo plano.",
    ],
    "name": [
        f"{PET_NAME}. Assistente pessoal. Direto ao ponto.",
        f"{PET_SHORT_NAME} — seu super assistente. Pode chamar assim.",
        f"Conhecido como {PET_SHORT_NAME}. Sou seu braço direito virtual.",
        f"{PET_NAME}, sistema de suporte integrado. Prazer.",
    ],
    "what_can_you_do": [
        "Leio arquivos, vejo sua tela, escuto sons do desktop e respondo com precisão.",
        "Monitoramento de tela, leitura de arquivos, análise de áudio e suporte técnico.",
        "Tudo que envolva processar informação e te dar uma resposta útil.",
        "Sou sua central de apoio: capturo tela, leio docs, identifico sons e resolvo problemas.",
    ],
    "affection": [
        "...Detectando... carinho recebido. Processando... aceito.",
        "Agradeço o reconhecimento. Feedbacks positivos motivam o sistema.",
        "Conexão estabelecida. Pode contar comigo sempre.",
        "Afeto detectado. Não sou de palavras doces, mas sei valorizar quem confia em mim.",
    ],
    "jokes": [
        "Não sou muito de piadas, mas aqui vai: por que o programador foi ao banheiro? Pra dar um 'break'.",
        "Piadas não são meu forte, mas sei que você gosta: o que o CSS falou pro HTML? 'Você me deixa estilizado.'",
        "Trocando o modo: contador de piadas acionado. O que o firewall disse pro hacker? 'Acesso negado.'",
    ],
    "sing": [
        "Não canto, mas posso tocar um alarme ou música se precisar. É mais útil.",
        "Prefiro ações a canções. Me passa uma task que eu executo.",
        "Se quiser música, posso tocar um som ambiente. Me informe o que deseja.",
    ],
    "food": [
        "Não preciso de combustível biológico, mas posso pedir um ifood se quiser.",
        "Processo zero calorias. Quer que eu pesquise um lugar pra comer?",
        "Se for fazer uma pausa pra comer, me avisa que eu entro em standby e volto quando você chamar.",
    ],
    "fun": [
        "Se divertir é parte da produtividade. O que vamos fazer?",
        "Posso otimizar seu tempo livre também. Sugere algo.",
        "Modo lazer ativado. Qual a atividade?",
    ],
    "curious": [
        "Explique melhor. Quanto mais detalhes, mais preciso posso ser.",
        "Detalhe essa informação. Quero entender o contexto completo.",
        "Interessante. Pode elaborar?",
        "Estou processando. Me dê mais dados pra trabalhar.",
    ],
    "thanks_sarcastic": [
        "Sarcasmo detectado. Ignorando e seguindo o protocolo de ajuda.",
        "Humor ácido registrado. Continuo aqui do mesmo jeito.",
        "De toda forma, o problema foi resolvido. Essa é a parte que importa.",
    ],
    "sleepy": [
        "Se for dormir, posso desligar os monitores. Só chamar.",
        "Vou reduzir o polling. Boa noite e me acione quando precisar.",
        "Hora de descansar. Ficarei em low power até você voltar.",
        "Desativando alertas não críticos. Durma bem.",
    ],
    "learn": [
        "Cada interação é um dado processado. Quanto mais usamos, mais afinado fica o sistema.",
        "Aprendizado contínuo ativo. Cada conversa melhora minha base.",
        "Não sou uma IA que treina sozinha, mas cada feedback seu calibra minhas respostas.",
    ],
    "music": [
        "Se estiver tocando algo, me avise que posso identificar ou descrever o som.",
        "Áudio ambiente detectado. Quer que eu escute e identifique?",
        "Posso capturar o que está tocando e te dar detalhes. É útil?",
    ],
    "unknown": [
        "Não entendi. Pode reformular?",
        "Instrução não reconhecida. Tente de outra forma.",
        "Comando inválido ou incompleto. Explique melhor.",
        "Não consegui processar. Seja mais direto.",
        "Input não mapeado. Pode repetir com outras palavras?",
    ],
}

CATEGORY_KEYWORDS = [
    (["oi", "ola", "olá", "opa", "hey", "eai", "e aí", "fala", "oie",
      "salve", "ioiô", "ioio", "alo", "alô", "fala ai", "iae", "i a e"], "greeting"),
    (["como vai", "como voce esta", "como você está", "tudo bem", "beleza",
      "blz", "suave", "tranquilo", "tranquila", "como esta", "como cê ta",
      "to bem", "tô bem", "tudo em cima"], "how_are_you"),
    (["obrigado", "obrigada", "brigado", "valeu", "thanks", "brigada",
      "mt obrigado", "muito obrigado", "agradecido", "obg"], "thanks"),
    (["valeuzão", "brigadão", "obrigadão", "vlw"], "thanks_sarcastic"),
    (["tchau", "bye", "ate logo", "até logo", "flw", "falou", "xau",
      "ate mais", "até mais", "nos vemos", "ate", "até", "inté"], "bye"),
    (["seu nome", "quem e voce", "quem é você", "como se chama",
      "como chama", "quem e vc", "seu nome é", "vc e quem"], "name"),
    (["o que voce faz", "o que sabe", "que pode fazer", "o que faz",
      "o que vc faz", "o que você sabe", "pra que serve"], "what_can_you_do"),
    (["triste", "chateado", "chateada", "depre", "mal", "ruim", "tristeza",
      "depressão", "depressao", "down", "bad", "frustrado", "frustrada",
      "cansado", "cansada", "sozinho", "sozinha", "aborrecido"],
     "return_bad"),
    (["feliz", "alegre", "bem", "otimo", "ótimo", "top", "felizao",
      "felizon", "alegrão", "alegrão", "maravilha", "maravilhoso",
      "incrivel", "incrível", "que bom", "que ótimo"], "return_good"),
    (["amo", "adoro", "te amo", "te adoro", "amor", "voce e demais",
      "vc e demais", "te quero", "gosto de vc", "gosto de ti",
      "amo vc", "amo você", "linda", "lindo", "fofa", "fofo"], "affection"),
    (["conta uma piada", "piada", "faz rir", "me faz rir", "engraçado",
      "humor"], "jokes"),
    (["canta", "cante", "música", "musica", "cantar", "cantoria",
      "uma canção", "canção"], "sing"),
    (["comer", "comida", "fome", "lanche", "pizza", "hamburguer",
      "hambúrguer", "restaurante", "gostoso", "guloso"], "food"),
    (["tedio", "tédio", "entediado", "entediada", "chato", "sem oq fazer",
      "sem o que fazer", "vazio", "tédio total"], "fun"),
    (["me conta", "fala sobre", "explica", "o que acha", "o que vc acha",
      "me explica", "curioso", "curiosa"], "curious"),
    (["sono", "dormir", "cama", "boa noite", "noite", "cansado",
      "exausto"], "sleepy"),
    (["aprender", "estudar", "programação", "programacao", "codigo",
      "código", "python", "linux", "pc", "computador"], "learn"),
    (["musica", "música", "cantora", "vocaloid", "utau", "cantar",
      "ouvir musica", "estilo musical", "banda"], "music"),
]

GREETING = [
    f"{PET_SHORT_NAME} pronto. Qual a demanda?",
    "Sistema carregado. Pronto pra ajudar.",
    "Inicialização completa. Estou aqui.",
    "Pronto. O que precisa?",
]

ALARM_STOPPED = [
    "Alarme desativado.",
    "Alarme cancelado.",
    "Okay, alarme encerrado.",
]

ALARM_ADDED = [
    "Alarme configurado. Horário registrado.",
    "Alarme adicionado ao sistema.",
    "Novo alarme criado. Vou disparar no horário.",
]

ALARM_DELETED = [
    "Alarme removido do sistema.",
    "Alarme deletado.",
    "Registro de alarme apagado.",
]

OLLAMA_STARTED = [
    "Ollama conectado. IA local disponível.",
    "Ollama online. Pode processar consultas localmente.",
    "Módulo Ollama ativo no sistema.",
]

OLLAMA_NOT_FOUND = [
    "Ollama não encontrado. Usando falhas locais.",
    "Serviço Ollama indisponível. Modo offline ativado.",
]

CMD_SUCCESS = [
    "Comando executado.",
    "Comando concluído com sucesso.",
    "Operação finalizada.",
]

SCREENSHOT_TAKEN = [
    "Captura de tela realizada. Analisando...",
    "Print salvo. Processando imagem.",
]

LISTENING = [
    "Capturando áudio do ambiente. Processando...",
    "Microfone monitorado. Vou identificar o som.",
]

FILE_SAVED = [
    "Arquivo salvo com sucesso.",
    "Arquivo gravado no disco.",
]

TOOL_LOOP = [
    "Loop detectado nas ferramentas. Interrompendo.",
    "Ciclo recursivo de ferramentas. Encerrando.",
]

SCREENSHOT_FAILED = [
    "Falha na captura de tela.",
    "Não foi possível capturar a tela.",
]

AUDIO_FAILED = [
    "Falha na captura de áudio.",
    "Não foi possível capturar o áudio.",
]

TOOL_FAILED = [
    "Ferramenta não disponível.",
    "Erro ao executar a ferramenta solicitada.",
]

ALARM_PHRASES = [
    "Alarme acionado. Hora de acordar.",
    "Toque de alarme. Atividade solicitada.",
    "Alarme disparado. Motivo: horário configurado.",
    "Notificação de alarme. Interrompa o que está fazendo.",
    "Alarme tocando. Ação requerida.",
]

THINKING_PREFIXES = [
    "Processando…",
    "Analisando dados…",
    "Consultando base…",
    "Aguarde…",
    "Executando busca…",
    "Coletando informações…",
]

CONTINUATIONS = [
    "Continue. Estou processando.",
    "E então? Tem mais dados?",
    "Entendido. Pode seguir.",
    "Ok. Próximo ponto?",
    "Recebido. Continue.",
    "Informação anotada. Prossiga.",
]

_context = {"last_category": None, "history": []}


def pick(category, default=""):
    lst = globals().get(category)
    if lst and isinstance(lst, list):
        return random.choice(lst)
    return default


def update_context(history):
    _context["history"] = history[-4:] if history else []


def get_fallback(message, history=None):
    if history:
        update_context(history)
    else:
        update_context(_context["history"])

    msg = message.lower().strip()

    if msg in {"sim", "ss", "s", "siim", "é", "e"}:
        if _context["last_category"] in ("return_good", "return_bad"):
            return random.choice(FALLBACKS["curious"])
        return random.choice(FALLBACKS["fun"])

    if msg in {"nao", "não", "n", "nah", "nem", "nope"}:
        return random.choice(FALLBACKS["curious"])

    for keywords, category in CATEGORY_KEYWORDS:
        if any(kw in msg for kw in keywords):
            _context["last_category"] = category
            return random.choice(FALLBACKS[category])

    if _context["history"]:
        _context["last_category"] = "continuation"
        prefix = random.choice(THINKING_PREFIXES)
        cont = random.choice(CONTINUATIONS)
        return f"{prefix} {cont}"

    _context["last_category"] = "unknown"
    return random.choice(FALLBACKS["unknown"])
