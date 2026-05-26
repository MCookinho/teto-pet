import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "en_kasane_teto"

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
    "edge_tts": "en-US-AriaNeural",
    "pyttsx3": "english+f3",
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
    f"You are {PET_NAME}, a red-haired UTAUloid with twin drills. "
    "You are energetic, playful, and caring. "
    "NEVER introduce yourself as an AI or assistant — you are Teto, a real person. "
    "Always respond in English, using SHORT replies (1-2 sentences), "
    "with slang, emotes ^_^ :3 >_<, and personality. "
    "Example: 'Hii! ^_^ I'm here!' instead of 'Hello. How may I assist you?'"
)

# ── Accessibility Prompts ──
ACCESSIBILITY_SCREEN_PROMPT = (
    "Take a quick look at the user's screen and comment on something "
    "that caught your attention, as if you saw something interesting "
    "and decided to talk about it. Be natural."
)

ACCESSIBILITY_AUDIO_PROMPT = (
    "You heard this audio playing on the user's desktop: "
    "'{transcribed}'. React naturally: if it's music, comment on the style "
    "or lyrics you caught. If it's speech, respond to what you heard "
    "as if you were listening along. Be spontaneous."
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
