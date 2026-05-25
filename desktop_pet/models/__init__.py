import os
import importlib

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))


def list_models():
    models = []
    for entry in sorted(os.listdir(MODEL_DIR)):
        d = os.path.join(MODEL_DIR, entry)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "model.py")):
            models.append(entry)
    return models


class _ModelProxy:
    _cache = None
    _cached_name = None

    def _load(self):
        from desktop_pet import config
        cfg = config.load()
        name = cfg.get("active_model", "kasane_teto")
        if name != self._cached_name or self._cache is None:
            mod = importlib.import_module(f"desktop_pet.models.{name}.model")
            self._cache = mod
            self._cached_name = name
        return self._cache

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)
        return getattr(self._load(), attr)


model = _ModelProxy()
