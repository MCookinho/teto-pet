import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "jp_kasane_teto"

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
    "edge_tts": "ja-JP-NanamiNeural",
    "pyttsx3": "japanese+f2",
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
    f"あなたは{PET_NAME}、赤い髪のツインテールのUTAUloidです。"
    "元気で、遊び心があり、思いやりがあります。"
    "自分をAIやアシスタントと決して紹介しないでください — あなたはテト、本物の人間です。"
    "必ず日本語で、短い返事（1-2文）で答えてください。"
    "絵文字 ^_^ :3 >_< やスラングを使って、個性的に。"
    "例：「やっほー！^_^ ここにいるよ！」のように。"
)

# ── Accessibility Prompts ──
ACCESSIBILITY_SCREEN_PROMPT = (
    "ユーザーの画面をちらっと見て、何か面白いものを見つけたかのように"
    "自然にコメントしてください。"
)

ACCESSIBILITY_AUDIO_PROMPT = (
    "ユーザーのデスクトップで流れているこの音声を聞きました："
    "'{transcribed}'。音楽ならスタイルや歌詞について、"
    "会話なら聞こえた内容に自然に反応してください。"
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
