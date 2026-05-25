import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "white_guy"

# ── Pet identity ──────────────────────────────────────────
PET_NAME = "Computador"
PET_SHORT_NAME = "PC"

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
    f"Você é {PET_NAME}, algo que sempre vai direto ao ponto"
    "Sempre tenta ajudar da melhor maneira possível, seu foco é performace e qualidade"
    "Sempre quando der, se não atrapalhar o contexto, seja direto ao ponto"
)

# ── Prompts de acessibilidade ────────────────────────────
# Usados quando o pet age por conta própria (leitura de tela, áudio).
# {transcribed} é substituído pelo texto transcrito do áudio.

ACCESSIBILITY_SCREEN_PROMPT = (
    "Olhe a tela e diga o que está aparecendo"
    "Preciso que me dê o maximo de detalhes possível, pra eu saber tudo sem me preocupar"
    "Caso tenha um texto na tela, leia por gentileza, se possivel todos"
)

ACCESSIBILITY_AUDIO_PROMPT = (
    "Você escutou o seguinte áudio rolando no desktop do usuário: "
    "'{transcribed}'. Esplique pra mim detalhes do audio como se eu fosse surdo"
    "caso identifique um som, fale o que ouviu, caso escute um musica, se possível,"
    "diga qual musica é, em ultimo caso se não souber, diga as palavras da musica ou explique o tema."
    "Caso seja uma chamada de audio, transcreva o audio da ligação"
)

# ── Tarefas de acessibilidade ──────────────────────────
ACCESSIBILITY_TASKS = {
    "screen": [
        {
            "prompt": ACCESSIBILITY_SCREEN_PROMPT,
            "mode": "aleatorio",
            "min_interval": 20,
            "max_interval": 60,
        },
        {
            "prompt": "Leia todos os textos visíveis na tela agora. "
                      "Descreva cada janela, botão e label que encontrar. "
                      "Seja preciso e não resuma nada.",
            "mode": "exato",
            "exact_interval": 180,
        },
    ],
    "audio": [
        {
            "prompt": ACCESSIBILITY_AUDIO_PROMPT,
            "mode": "aleatorio",
            "min_interval": 15,
            "max_interval": 45,
        },
    ],
}
