import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Identity ──────────────────────────────────────────────
# These are used to identify your pet model.
MODEL_ID = "custom_model"              # Folder name (lowercase, no spaces)
PET_NAME = "My Pet"                    # Full display name
PET_SHORT_NAME = "Pet"                 # Short name shown in chat

# ── Sprites ───────────────────────────────────────────────
# Maps mood names to sprite filenames (without extension).
# The system looks for PNG or GIF in the sprites/ folder.
# Each mood can have a Speaking variant (e.g. "HappySpeaking").
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
    "Danca": "Dancing",
}

# ── Audio ─────────────────────────────────────────────────
# Optional ringtone for alarms. Set to None to disable.
RINGTONE_PATH = None  # or: os.path.join(MODEL_DIR, "ringtone.mp3")

# ── Font ──────────────────────────────────────────────────
# Optional custom font. Falls back to system default if unset.
FONT_NAME = None  # e.g. "Pixelify Sans"
FONT_SIZE = 13

# ── AI System Prompt ──────────────────────────────────────
# This defines your pet's personality. The AI uses this as
# its system instruction. Be creative!
#   {PET_NAME}       → replaced with PET_NAME
#   {PET_SHORT_NAME}  → replaced with PET_SHORT_NAME
SYSTEM_PROMPT = (
    f"Voce e {PET_NAME}, um mascote de desktop amigavel.\n"
    "- Responda em portugues brasileiro\n"
    "- Seja breve (1-2 frases)\n"
    "- Use emoticons as vezes\n"
    "- NUNCA diga que e uma IA"
)

# ── Accessibility Prompts ─────────────────────────────────
# These prompts are sent to the AI when automatically
# describing the screen or transcribing audio.
ACCESSIBILITY_SCREEN_PROMPT = (
    "Descreva o que voce ve nesta captura de tela "
    "em portugues, com detalhes interessantes."
)
ACCESSIBILITY_AUDIO_PROMPT = (
    "Comente sobre o que foi falado neste audio "
    "de forma natural."
)

# ── Accessibility Tasks ───────────────────────────────────
# Automatic background tasks. Set "mode" to "aleatorio"
# with min/max intervals (in seconds), or "exato" for
# a fixed interval.
ACCESSIBILITY_TASKS = {
    "screen": [
        {"mode": "aleatorio", "min": 15, "max": 60,
         "prompt": ACCESSIBILITY_SCREEN_PROMPT},
    ],
    "audio": [
        {"mode": "aleatorio", "min": 10, "max": 30,
         "prompt": ACCESSIBILITY_AUDIO_PROMPT},
    ],
}

# ── TTS Voices ─────────────────────────────────────────────
# Voice identifiers for each TTS provider.
# Leave empty strings to use provider defaults.
TTS_VOICE = {
    "fish_audio": "",
    "edge_tts": "pt-BR-FranciscaNeural",
    "pyttsx3": "brazil",
}
