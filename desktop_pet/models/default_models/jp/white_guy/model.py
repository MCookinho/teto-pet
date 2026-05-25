import os

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ID = "jp_white_guy"

# ── Identity ──
PET_NAME = "コンピュータ"
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
    "edge_tts": "ja-JP-KeitaNeural",
    "pyttsx3": "japanese+m2",
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
    f"あなたは{PET_NAME}です。いつも要点を直接伝えます。"
    "最善の方法で助けることを心がけ、パフォーマンスと品質に重点を置いています。"
    "可能な限り、文脈の邪魔にならない場合は、簡潔に答えてください。"
)

# ── Accessibility Prompts ──
ACCESSIBILITY_SCREEN_PROMPT = (
    "画面を見て、何が表示されているか教えてください。"
    "できるだけ詳細に説明し、すべてを把握できるようにしてください。"
    "画面にテキストがある場合は、できればすべて読んでください。"
)

ACCESSIBILITY_AUDIO_PROMPT = (
    "ユーザーのデスクトップで流れている音声を聞きました："
    "'{transcribed}'。まるで耳が聞こえないかのように詳細を説明してください。"
    "音を特定できた場合は、何を聞いたか言ってください。"
    "音楽の場合は、可能なら曲名を言ってください。"
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
            "prompt": "画面にある表示可能なテキストをすべて読んでください。"
                      "すべてのウィンドウ、ボタン、ラベルを説明してください。",
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
