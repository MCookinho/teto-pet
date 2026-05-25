import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
#  CUSTOM MODEL TEMPLATE
# ═══════════════════════════════════════════════════════════════
#
#  Directory structure your model folder MUST have:
#
#  models/{your_model}/
#  ├── __init__.py          (empty file — makes it a package)
#  ├── model.py             ← THIS FILE (your config here)
#  ├── phrases.py           ← fallback dialogue lines
#  └── sprites/
#       ├── Default.png     ← idle sprite
#       ├── DefaultSpeaking.png
#       ├── Happy.png       ← detected "feliz" mood
#       ├── HappySpeaking.png
#       ├── Sad.png         ← detected "triste" mood
#       ├── SadSpeaking.png
#       ├── Angry.png       ← detected "bravo/raiva" mood
#       ├── AngrySpeaking.png
#       ├── Dancing.png     ← alarm ringing
#       └── ... (can also be .gif for animation)
#
#  UI strings are now CENTRALIZED in desktop_pet/strings.py
#  — you don't need a strings.py in your model folder.
#
# ═══════════════════════════════════════════════════════════════


# ── Identity ─────────────────────────────────────────────────
# MODEL_ID must match the folder name (lowercase, no spaces).
# PET_NAME is the full display name.
# PET_SHORT_NAME is shown in chat bubbles.
MODEL_ID = "custom_model"
PET_NAME = "My Pet"
PET_SHORT_NAME = "Pet"


# ── Sprites ──────────────────────────────────────────────────
# SPRITES_DIR: path to the sprites folder (auto‑set above).
#
# SPRITE_NAMES: maps each mood (internal name) to the sprite
# file basename (without extension). The system looks for:
#   {basename}.png       — static sprite
#   {basename}.gif       — animated sprite (GIF)
#   {basename}Speaking.png / .gif — talking variant
#
# If a Speaking variant is missing, the non‑talking sprite is
# used even when the character talks (no visual change).
#
# ── Moods you MUST define ──
#   "Normal" → Default     idle / neutral
#   "Feliz"  → Happy      user is happy / positive words
#   "Triste" → Sad        user is sad / negative words
#   "Raiva"  → Angry      user is angry / frustrated
#   "Dança"  → Dancing    alarm is ringing
#
# ── Sprite format ──
# Recommended: 32×32 pixels per frame, PNG with transparency.
# For animated GIFs, all frames are packed horizontally into a
# single spritesheet. The system auto‑detects frame boundaries.
#
# What happens if a file is missing:
#   - Missing mood → falls back to the first mood that exists
#   - Missing Speaking variant → uses non‑talking version
#   - No sprites at all → fallback text is drawn on screen
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
    "Dança": "Dancing",
}


# ── Audio ────────────────────────────────────────────────────
# Path to an MP3 file played when an alarm goes off.
# Set to None to disable alarm sound.
RINGTONE_PATH = None  # or: os.path.join(MODEL_DIR, "ringtone.mp3")


# ── Background ───────────────────────────────────────────────
# When Wallpaper mode is ON, this image is drawn as the desktop
# background behind the pet. The image auto‑scales to fill any
# monitor. No file → transparent background.
# Uncomment the line below to enable:
# BACKGROUND_PATH = os.path.join(MODEL_DIR, "background.jpg")


# ── Font ─────────────────────────────────────────────────────
# Custom font for the speech bubble text.
# Set to None to use the system default.
# You can install a .ttf in the model folder and reference the
# font family name here (e.g. "Pixelify Sans").
FONT_NAME = None
FONT_SIZE = 13


# ── AI System Prompt ─────────────────────────────────────────
# This defines your pet's personality. The AI receives this as
# its system instruction on every chat message.
#
# Tips:
#   • Use {PET_NAME} and {PET_SHORT_NAME} — they're replaced
#     automatically at runtime.
#   • Keep it concise (2‑5 sentences). The AI follows it well.
#   • Specify the language you want the pet to speak.
#   • Add behavioral notes like "always be cheerful" or "use
#     emoticons".
#   • Avoid "you are an AI" — it breaks the illusion.
SYSTEM_PROMPT = (
    f"Voce e {PET_NAME}, um mascote de desktop amigavel.\n"
    "- Responda em portugues brasileiro\n"
    "- Seja breve (1-2 frases)\n"
    "- Use emoticons as vezes\n"
    "- NUNCA diga que e uma IA"
)


# ── Accessibility Prompts ────────────────────────────────────
# Sent to the AI when it automatically describes the screen
# (Screen Reading) or transcribes desktop audio.
# Write them in the same language as SYSTEM_PROMPT.
ACCESSIBILITY_SCREEN_PROMPT = (
    "Descreva o que voce ve nesta captura de tela "
    "em portugues, com detalhes interessantes."
)
ACCESSIBILITY_AUDIO_PROMPT = (
    "Comente sobre o que foi falado neste audio "
    "de forma natural."
)


# ── Accessibility Tasks ──────────────────────────────────────
# Automatic background tasks. Each task runs on an interval:
#   "aleatorio" — random interval between min and max seconds
#   "exato"     — fixed interval (use min for the value)
#
# Available task types:
#   "screen" — takes a screenshot and asks the AI to describe it
#   "audio"  — records desktop audio and asks the AI to transcribe
#
# You can add multiple entries per task type.
# Disable by setting the list to empty [].
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


# ── TTS Voices ───────────────────────────────────────────────
# Voice identifiers for each TTS provider.
# Leave empty strings to use the provider default.
#
# edge_tts: use full voice names like "pt-BR-FranciscaNeural"
#   Run `edge-tts --list-voices` to see all available.
#
# pyttsx3: use locale+gender like "brazil+m2"
#   Common: "brazil+m1" (male), "brazil+m2" (female),
#   "english+m1", "english+m2"
#
# fish_audio: voice ID from the Fish Audio API (optional)
TTS_VOICE = {
    "fish_audio": "",
    "edge_tts": "pt-BR-FranciscaNeural",
    "pyttsx3": "brazil",
}
