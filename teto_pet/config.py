import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/teto-pet")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

PROVIDER_AUTO = "auto"
PROVIDER_OLLAMA = "ollama"
PROVIDER_HF = "huggingface"
PROVIDER_PHRASES = "phrases"

PROVIDERS = [PROVIDER_AUTO, PROVIDER_OLLAMA, PROVIDER_HF, PROVIDER_PHRASES]

DEFAULT_CONFIG = {
    "window_x": 100,
    "window_y": 100,
    "always_on_top": True,
    "ai_provider": PROVIDER_AUTO,
    "language": "pt",
}


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
        # migrate old config: ai_enabled=False  ->  provider=phrases
        if "ai_enabled" in saved and not saved["ai_enabled"]:
            cfg["ai_provider"] = PROVIDER_PHRASES
    except (json.JSONDecodeError, OSError):
        pass

    return cfg


def save(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
