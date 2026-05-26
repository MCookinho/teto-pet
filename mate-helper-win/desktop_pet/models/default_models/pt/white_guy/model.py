import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "white_guy"

# ── Identity ──
PET_NAME = "Computador"
PET_SHORT_NAME = "PC"

from . import phrases as _phrases
phrases = _phrases

# ── TTS Voice ──
# Voice IDs for each provider.
#  fish_audio: leave empty; user sets via menu
#  edge_tts  : Microsoft Edge TTS voice name
#  pyttsx3   : espeak voice identifier
TTS_VOICE = {
    "fish_audio": "",
    "edge_tts": "pt-BR-AntonioNeural",
    "pyttsx3": "brazil+m2",
}

# ── Sprites ──
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
    "Dança": "Dancing",
}

# ── Ringtone ──
RINGTONE_PATH = os.path.join(MODEL_DIR, "ringtone.mp3")

# ── Font ──
FONT_NAME = "Pixelify Sans"
FONT_SIZE = 13

# ── AI System Prompt ──
SYSTEM_PROMPT = (
    f"Você é {PET_NAME}, algo que sempre vai direto ao ponto"
    "Sempre tenta ajudar da melhor maneira possível, seu foco é performace e qualidade"
    "Sempre quando der, se não atrapalhar o contexto, seja direto ao ponto"
)

# ── Accessibility Prompts ──
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

# ── Accessibility Tasks ──
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
