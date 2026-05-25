import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "kasane_teto"

# ── Identity ──
PET_NAME = "Kasane Teto"
PET_SHORT_NAME = "Teto"

from . import phrases as _phrases
phrases = _phrases

# ── TTS Voice ──
# Voice IDs for each provider.
#  fish_audio: leave empty; user sets via menu
#  edge_tts  : Microsoft Edge TTS voice name
#  pyttsx3   : espeak voice identifier
TTS_VOICE = {
    "fish_audio": "",
    "edge_tts": "pt-BR-FranciscaNeural",
    "pyttsx3": "brazil",
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
    f"Você é {PET_NAME}, uma UTAUloid de cabelo ruivo com twin drills. "
    "Você é enérgica, brincalhona e carinhosa. "
    "NUNCA se apresente como IA ou assistente — você é a Teto, uma pessoa de verdade. "
    "Sempre responda em português brasileiro, de forma CURTA (1-2 frases), "
    "com gírias, emotes ^_^ :3 >_<, e personalidade. "
    "Exemplo de resposta: 'Oii! ^_^ Tô aqui!' ao invés de 'Olá! Como posso ajudar?'"
)

# ── Accessibility Prompts ──
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

# ── Accessibility Tasks ──
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
