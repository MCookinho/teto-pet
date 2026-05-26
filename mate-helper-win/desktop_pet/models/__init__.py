import os
import importlib

from desktop_pet import strings as _ui_strings

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_MODELS_DIR = os.path.join(MODEL_DIR, "default_models")


def list_models():
    from desktop_pet import config
    cfg = config.load()
    lang = cfg.get("language", "pt")

    models = []

    lang_dir = os.path.join(LANG_MODELS_DIR, lang)
    if os.path.isdir(lang_dir):
        for entry in sorted(os.listdir(lang_dir)):
            d = os.path.join(lang_dir, entry)
            if os.path.isdir(d) and os.path.isfile(os.path.join(d, "model.py")):
                models.append(entry)

    for entry in sorted(os.listdir(MODEL_DIR)):
        if entry == "default_models":
            continue
        d = os.path.join(MODEL_DIR, entry)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "model.py")):
            if entry not in models:
                models.append(entry)

    return models


class _ModelProxy:
    _cache = None
    _cached_name = None
    _cached_lang = None

    def _load(self):
        from desktop_pet import config
        cfg = config.load()
        name = cfg.get("active_model", "kasane_teto")
        lang = cfg.get("language", "pt")
        if name != self._cached_name or lang != self._cached_lang or self._cache is None:
            try:
                mod = importlib.import_module(
                    f"desktop_pet.models.default_models.{lang}.{name}.model"
                )
            except (ImportError, ModuleNotFoundError):
                mod = importlib.import_module(f"desktop_pet.models.{name}.model")
            self._cache = mod
            self._cached_name = name
            self._cached_lang = lang
        return self._cache

    def get_string(self, lang_code, key, **kwargs):
        lang_dict = _ui_strings.STRINGS.get(lang_code, {})
        text = lang_dict.get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        return getattr(self._load(), attr)


model = _ModelProxy()
