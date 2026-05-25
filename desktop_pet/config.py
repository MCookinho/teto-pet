import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/teto-pet")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

PROVIDER_AUTO = "auto"
PROVIDER_OLLAMA = "ollama"
PROVIDER_HF = "huggingface"
PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ = "groq"
PROVIDER_PHRASES = "phrases"

PROVIDERS = [PROVIDER_AUTO, PROVIDER_OLLAMA, PROVIDER_HF, PROVIDER_GEMINI, PROVIDER_GROQ, PROVIDER_PHRASES]

TTS_PROVIDER_AUTO = "auto"
TTS_PROVIDER_FISH = "fish_audio"
TTS_PROVIDER_EDGE = "edge_tts"
TTS_PROVIDER_PYTTS = "pyttsx3"

TTS_PROVIDERS = [TTS_PROVIDER_AUTO, TTS_PROVIDER_FISH, TTS_PROVIDER_EDGE, TTS_PROVIDER_PYTTS]

BUBBLE_AUTO = "auto"
BUBBLE_LEFT = "left"
BUBBLE_RIGHT = "right"
BUBBLE_SIDES = [BUBBLE_AUTO, BUBBLE_LEFT, BUBBLE_RIGHT]

# Per-tool permission keys
TOOL_KEYS = [
    "tool_read_file",
    "tool_list_files",
    "tool_run_command",
    "tool_write_file",
    "tool_open_url",
    "tool_screenshot",
    "tool_listen",
]

DEFAULT_CONFIG = {
    "window_x": 100,
    "window_y": 100,
    "always_on_top": True,
    "ai_provider": PROVIDER_AUTO,
    "language": "pt",
    "gemini_key": "",
    "groq_key": "",
    "hf_token": "",
    "bubble_side": BUBBLE_AUTO,
    "active_model": "kasane_teto",
    "ollama_model": "",
    "user_name": "",
    "user_bio": "",
    "accessibility_enabled": False,
    "accessibility_mode": "aleatorio",
    "accessibility_interval": 30,
    "accessibility_min_interval": 15,
    "accessibility_max_interval": 60,
    "accessibility_audio_enabled": False,
    "accessibility_audio_mode": "aleatorio",
    "accessibility_audio_interval": 10,
    "accessibility_audio_min_interval": 5,
    "accessibility_audio_max_interval": 30,
    "accessibility_speech_enabled": False,
    "speech_mode": "aleatorio",
    "speech_min_interval": 30,
    "speech_max_interval": 120,
    "speech_exact_interval": 60,
    "mic_stt_enabled": False,
    "mic_stt_device": "",
    "mic_stt_mode": "toggle",
    "stt_shortcut": "V",
    "window_scale": 5,
    "wallpaper_enabled": False,
    "speech_behavior": "interrupt",
    "accessibility_use_model_defaults": False,
    "tts_enabled": False,
    "tts_provider": TTS_PROVIDER_AUTO,
    "tts_device": "",
    "tts_volume": 100,
    "fish_audio_key": "",
    "fish_audio_voice": "",
    "alarms": [
        {"hour": 8, "minute": 0, "enabled": False, "name": ""},
    ],
}
for k in TOOL_KEYS:
    DEFAULT_CONFIG[k] = False


def load():
    cfg = dict(DEFAULT_CONFIG)

    if not os.path.exists(CONFIG_FILE):
        return cfg

    try:
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        for k in cfg:
            if k in saved:
                cfg[k] = saved[k]
        # validate provider
        if cfg["ai_provider"] not in PROVIDERS:
            cfg["ai_provider"] = PROVIDER_AUTO
        # validate bubble_side
        if cfg.get("bubble_side") not in BUBBLE_SIDES:
            cfg["bubble_side"] = BUBBLE_AUTO
        # migrate old config: ai_enabled=False  ->  provider=phrases
        if "ai_enabled" in saved and not saved["ai_enabled"]:
            cfg["ai_provider"] = PROVIDER_PHRASES
        # migrate old assistente_local -> individual tool flags
        if "assistente_local" in saved and saved["assistente_local"]:
            for k in TOOL_KEYS:
                if k not in saved:
                    cfg[k] = True
    except (json.JSONDecodeError, OSError):
        pass

    return cfg


def save(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
