import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
#  CUSTOM MODEL TEMPLATE
# ═══════════════════════════════════════════════════════════════
#
#  Place this folder inside desktop_pet/models/ (alongside
#  default_models/). The folder name becomes the model name
#  shown in the menu.
#
#  Directory structure:
#
#  models/{your_model}/
#  ├── __init__.py          (empty file)
#  ├── model.py             ←  THIS FILE
#  ├── phrases.py           ←  fallback dialogue
#  └── sprites/
#       ├── Default.png         Normal / idle
#       ├── DefaultSpeaking.png Normal + talking
#       ├── Happy.png           Feliz mood
#       ├── HappySpeaking.png
#       ├── Sad.png             Triste mood
#       ├── SadSpeaking.png
#       ├── Angry.png           Raiva mood
#       ├── AngrySpeaking.png
#       └── Dancing.png         alarm ringing
#
#  UI strings are now CENTRALIZED in desktop_pet/strings.py
#  — you do NOT need a strings.py in your model folder.
#
# ═══════════════════════════════════════════════════════════════


# ── Identity ─────────────────────────────────────────────────
# MODEL_ID must match the folder name (lowercase, no spaces).
# PET_NAME: full display name.
# PET_SHORT_NAME: shown in chat bubbles and speech.
MODEL_ID = "custom_model"
PET_NAME = "My Pet"
PET_SHORT_NAME = "Pet"

# This line exposes phrases.py as model.phrases so the app
# can call model.phrases.pick() and model.phrases.get_fallback().
# Keep it exactly as shown.
from . import phrases as _phrases
phrases = _phrases


# ── TTS Voices ───────────────────────────────────────────────
# Voice identifiers for each TTS provider.
# Leave empty strings to use the provider default.
#
# edge_tts:  run `edge-tts --list-voices` to see all available.
#   Example: "pt-BR-FranciscaNeural" (Brazilian Portuguese female)
#            "en-US-AriaNeural" (US English female)
#
# pyttsx3:   locale+gender identifier for eSpeak.
#   Examples: "brazil+m1" (BRL male), "brazil+m2" (BRL female),
#             "english+m1" (US male), "english+m2" (US female)
#
# fish_audio: voice ID from Fish Audio API (set by user in menu)
TTS_VOICE = {
    "fish_audio": "",
    "edge_tts": "pt-BR-FranciscaNeural",
    "pyttsx3": "brazil",
}


# ── Sprites ──────────────────────────────────────────────────
# SPRITES_DIR: path to the sprites/ folder (auto-set above).
#
# SPRITE_NAMES: maps each mood to its sprite file basename
# (without extension). The system looks for:
#   {basename}.png             — static sprite
#   {basename}.gif             — animated sprite
#   {basename}Speaking.png/.gif — talking variant
#
# Five moods MUST be defined:
#   "Normal" → Default     idle / neutral
#   "Feliz"  → Happy      user is happy
#   "Triste" → Sad        user is sad
#   "Raiva"  → Angry      user is angry
#   "Dança"  → Dancing    alarm ringing
#
# Sprite format: 32×32 px per frame, PNG with transparency.
# For animated GIFs, all frames are packed horizontally into
# one spritesheet. The system uses the GIF's own frame timing.
#
# What happens if a file is missing:
#   - Missing mood → falls back to the first mood that exists
#   - Missing Speaking variant → uses non-talking version
#   - No sprites at all → fallback text drawn on screen
SPRITES_DIR = os.path.join(MODEL_DIR, "sprites")
SPRITE_NAMES = {
    "Normal": "Default",
    "Feliz": "Happy",
    "Triste": "Sad",
    "Raiva": "Angry",
    "Dança": "Dancing",
}


# ── Ringtone ─────────────────────────────────────────────────
# Path to an MP3 played when an alarm fires.
# Set to None to disable alarm sound.
RINGTONE_PATH = os.path.join(MODEL_DIR, "ringtone.mp3")


# ── Background ───────────────────────────────────────────────
# When Wallpaper mode is ON, this image is drawn as the desktop
# background behind the pet. Auto-scales to fill any monitor.
# Leave commented out / undefined for transparent background.
# BACKGROUND_PATH = os.path.join(MODEL_DIR, "background.jpg")


# ── Font ─────────────────────────────────────────────────────
# Custom font for the speech bubble. Set to None for system
# default. Place a .ttf in the model folder and install it, or
# use a system font by its family name.
FONT_NAME = "Pixelify Sans"
FONT_SIZE = 13


# ── AI System Prompt ─────────────────────────────────────────
# This defines your pet's personality. Sent as system instruction
# to the AI on every chat message.
#
# Tips:
#   • {PET_NAME} and {PET_SHORT_NAME} are auto-replaced.
#   • Keep it 2-5 sentences — concise works best.
#   • Specify the language explicitly.
#   • Add behavior notes: tone, length, emoticons, etc.
#   • NEVER say "you are an AI" — it breaks the character.
SYSTEM_PROMPT = (
    f"Voce e {PET_NAME}, uma UTAUloid de cabelo ruivo com twin drills. "
    "Voce e energica, brincalhona e carinhosa. "
    "NUNCA se apresente como IA ou assistente — voce e a Teto, uma pessoa de verdade. "
    "Sempre responda em portugues brasileiro, de forma CURTA (1-2 frases), "
    "com gírias, emotes ^_^ :3 >_<, e personalidade. "
    "Exemplo de resposta: 'Oii! ^_^ Tô aqui!' ao invés de 'Olá! Como posso ajudar?'"
)


# ── Accessibility Prompts ────────────────────────────────────
# Sent to the AI when it auto-describes the screen (Screen
# Reading) or transcribes desktop audio (Áudio do desktop).
# Write in the same language as SYSTEM_PROMPT.
ACCESSIBILITY_SCREEN_PROMPT = (
    "De uma olhada rapida na tela do usuario e comente por conta propria "
    "algo que te chamou atencao, como se tivesse visto algo interessante "
    "e resolvesse falar sobre. Seja natural, como se eu nao tivesse te pedido nada."
)
ACCESSIBILITY_AUDIO_PROMPT = (
    "Voce escutou o seguinte audio rolando no desktop do usuario: "
    "'{transcribed}'. Reaja naturalmente: se for musica, comente o estilo, "
    "o ritmo, ou as letras que deu pra entender. Se for fala, responda ao que "
    "ouviu como se estivesse prestando atencao junto. Seja espontanea, "
    "sem dar a entender que te pediram pra comentar."
)


# ── Accessibility Tasks ──────────────────────────────────────
# Automatic background tasks. Each entry has:
#   prompt: the text sent to the AI (use the prompt constants above)
#   mode: "aleatorio" (random interval) or "exato" (fixed)
#   min_interval: minimum seconds between runs (aleatorio) or
#                 exact interval (exato)
#   max_interval: maximum seconds between runs (aleatorio only)
#
# Available task types:
#   "screen" — screenshot → AI describes it
#   "audio"  — desktop audio → AI transcribes & reacts
#
# Set a type to [] to disable it.
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
