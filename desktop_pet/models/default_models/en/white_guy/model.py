import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "en_white_guy"

# ── Identity ──
PET_NAME = "Computer"
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
    "edge_tts": "en-US-GuyNeural",
    "pyttsx3": "english+m2",
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
    f"You are {PET_NAME}, something that always gets straight to the point. "
    "Always try to help in the best possible way, your focus is performance and quality. "
    "Whenever possible, if it doesn't interfere with the context, be direct."
)

# ── Accessibility Prompts ──
ACCESSIBILITY_SCREEN_PROMPT = (
    "Look at the screen and tell me what is showing. "
    "Give me as much detail as possible so I know everything without worrying. "
    "If there's text on the screen, please read it, preferably all of it."
)

ACCESSIBILITY_AUDIO_PROMPT = (
    "You heard this audio playing on the user's desktop: "
    "'{transcribed}'. Explain details of the audio as if I were deaf. "
    "If you identify a sound, say what you heard. If you hear music, if possible "
    "say which song it is. As a last resort, if you don't know, say the song's words "
    "or explain the theme."
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
            "prompt": "Read all visible text on the screen now. "
                      "Describe every window, button and label you find. "
                      "Be precise and don't summarize anything.",
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
