import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/teto-pet")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "window_x": 100,
    "window_y": 100,
    "always_on_top": True,
    "ai_enabled": True,
    "ai_provider": "huggingface",
    "ai_endpoint": "http://localhost:11434/api/generate",
    "ai_model": "llama3.2",
    "language": "pt",
}


def load():
    if not os.path.exists(CONFIG_FILE):
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(cfg)
            return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)


def save(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
