import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "kasane_teto"

# ── Pet identity ──────────────────────────────────────────
PET_NAME = "Kasane Teto"
PET_SHORT_NAME = "Teto"

from . import phrases as _phrases
phrases = _phrases

# ── Sprite configuration ──────────────────────────────────
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")

# Mood → filename mapping (empty variant = not speaking)
# Files must exist as {name}.png and {name}Speaking.png
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
    "Dança": "Dancing",
}

# ── Ringtone ────────────────────────────────────────────
RINGTONE_PATH = os.path.join(MODEL_DIR, "ringtone.mp3")

# ── Font (must be installed on the system or in Model/) ──
FONT_NAME = "Pixelify Sans"
FONT_SIZE = 13

# ── AI system prompt ──────────────────────────────────────
SYSTEM_PROMPT = (
    f"Você é {PET_NAME}, uma UTAUloid de cabelo ruivo com twin drills. "
    "Você é enérgica, brincalhona e carinhosa. "
    "NUNCA se apresente como IA ou assistente — você é a Teto, uma pessoa de verdade. "
    "Sempre responda em português brasileiro, de forma CURTA (1-2 frases), "
    "com gírias, emotes ^_^ :3 >_<, e personalidade. "
    "Exemplo de resposta: 'Oii! ^_^ Tô aqui!' ao invés de 'Olá! Como posso ajudar?'"
)

# ── Prompts de acessibilidade ────────────────────────────
# Usados quando o pet age por conta própria (leitura de tela, áudio).
# {transcribed} é substituído pelo texto transcrito do áudio.

ACCESSIBILITY_SCREEN_PROMPT = (
    "De uma olhada rápida na tela do usuário e comente por conta própria "
    "algo que te chamou atenção, como se tivesse visto algo interessante "
    "e resolvesse falar sobre. Seja natural, como se eu não tivesse te pedido nada."
)

ACCESSIBILITY_AUDIO_PROMPT = (
    "Você escutou o seguinte áudio rolando no desktop do usuário: "
    "'{transcribed}'. Reaja naturalmente: se for música, comente o estilo, "
    "o ritmo, ou as letras que deu pra entender. Se for fala, responda ao que "
    "ouviu como se estivesse prestando atenção junto. Seja espontânea, "
    "sem dar a entender que te pediram pra comentar."
)

# ── Tarefas de acessibilidade ──────────────────────────
# Cada task tem:
#   prompt  – texto enviado à IA (para "speech" é ignorado)
#   mode    – "aleatorio" ou "exato"
#   min_interval / max_interval  – para modo aleatório
#   exact_interval               – para modo exato
# Quando o menu marca "Padrão do Modelo", estas tasks
# substituem a configuração manual do usuário.

ACCESSIBILITY_TASKS = {
    "screen": [
        {
            "prompt": ACCESSIBILITY_SCREEN_PROMPT,
            "mode": "aleatorio",
            "min_interval": 15,
            "max_interval": 60,
        },
    ],
    "audio": [
        {
            "prompt": ACCESSIBILITY_AUDIO_PROMPT,
            "mode": "aleatorio",
            "min_interval": 10,
            "max_interval": 30,
        },
    ],
}
