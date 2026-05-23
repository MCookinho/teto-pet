import json
import urllib.request
import urllib.error

from teto_pet import config
from teto_pet import phrases


def ask(message, history=None):
    cfg = config.load()
    if cfg.get("ai_enabled") and cfg.get("ai_endpoint"):
        try:
            return _ask_ollama(message, history or [], cfg)
        except Exception:
            pass

    return _ask_fallback(message)


def _ask_ollama(message, history, cfg):
    endpoint = cfg["ai_endpoint"]
    model = cfg.get("ai_model", "llama3.2")

    messages = [{"role": "system",
                 "content": "Você é a Kasane Teto, uma vocaloid energética e brincalhona. "
                            "Responda de forma curta, fofa e em português. "
                            "Use emoticons e seja carismática como uma mascote de desktop."}]
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    return data.get("response", "").strip()


def _ask_fallback(message):
    return phrases.get_fallback(message)
