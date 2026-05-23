import sys
import threading
import socket

import requests
from gi.repository import GLib

from teto_pet import phrases

SYSTEM = (
    "You are Kasane Teto, an energetic and playful UTAU vocaloid. "
    "Keep answers short (1-2 sentences), cute, and in Portuguese (Brazilian). "
    "Use emoticons like ^_^, :3, >_<, etc. "
    "You are a desktop companion and best friend."
)

API_TIMEOUT = 10


def ask(message, history=None, callback=None):
    if not history:
        history = []
    if callback is None:
        return _try_all(message, history)
    thread = threading.Thread(
        target=lambda: GLib.idle_add(callback, _try_all(message, history)),
        daemon=True,
    )
    thread.start()


def _try_all(message, history):
    reply = _ask_ollama(message, history)
    if reply:
        return reply

    reply = _ask_hf(message, history)
    if reply:
        return reply

    print("[teto-pet] All AIs failed, using fallback phrases", file=sys.stderr)
    return phrases.get_fallback(message)


def _domain_reachable(host, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


def _ask_ollama(message, history):
    model = _ollama_model()
    if not model:
        return None

    prompt = f"{SYSTEM}\n"
    for h in history[-6:]:
        prompt += f"{'User' if h['role'] == 'user' else 'Teto'}: {h['content']}\n"
    prompt += "Teto:"

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False,
                  "options": {"num_predict": 80, "temperature": 0.8}},
            timeout=15,
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "")
            if text:
                for prefix in ("Teto:", "teto:", "Assistente:", "assistente:"):
                    if text.startswith(prefix):
                        text = text[len(prefix):]
                text = text.strip()
                print(f"[teto-pet] Ollama ({model}): {text[:60]}", file=sys.stderr)
                return text
    except requests.RequestException as e:
        print(f"[teto-pet] Ollama error: {e}", file=sys.stderr)

    return None


def _ollama_model():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return None
        models = resp.json().get("models", [])
        if not models:
            return None
        # prefer smaller models first (faster responses)
        model_names = [m["name"] for m in models]
        # pick the smallest (or first) model
        model_names.sort(key=lambda n: n)
        chosen = model_names[0]
        print(f"[teto-pet] Ollama detectado: {chosen}", file=sys.stderr)
        return chosen
    except requests.RequestException:
        return None


def _ask_hf(message, history):
    if not _domain_reachable("api-inference.huggingface.co"):
        print("[teto-pet] HuggingFace domain unreachable, skipping", file=sys.stderr)
        return None

    models = [
        "HuggingFaceH4/zephyr-7b-beta",
        "microsoft/DialoGPT-medium",
    ]

    for model in models:
        prompt = _build_prompt(model, message, history)
        try:
            resp = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                json={"inputs": prompt, "parameters": _params(model)},
                timeout=API_TIMEOUT,
                headers={"User-Agent": "teto-pet/1.0"},
            )
        except requests.RequestException as e:
            print(f"[teto-pet] HF {model} error: {e}", file=sys.stderr)
            continue

        if resp.status_code == 503:
            print(f"[teto-pet] HF {model} loading (503)", file=sys.stderr)
            continue
        if resp.status_code != 200:
            print(f"[teto-pet] HF {model} status {resp.status_code}", file=sys.stderr)
            continue

        try:
            data = resp.json()
        except ValueError:
            continue

        text = _extract(data)
        if not text:
            continue

        after = text.split("Teto:")[-1].strip()
        if after and not after.startswith("User:"):
            return after

    return None


def _params(model):
    base = {"max_new_tokens": 60, "temperature": 0.8, "top_p": 0.9, "do_sample": True}
    if "DialoGPT" in model:
        base["max_new_tokens"] = 80
    return base


def _build_prompt(model, message, history):
    if "zephyr" in model:
        p = f"<|system|>\n{SYSTEM}\n"
        for h in history[-6:]:
            role = h["role"]
            p += f"<|{'user' if role == 'user' else 'assistant'}|>\n{h['content']}\n"
        p += "<|assistant|>\n"
    else:
        p = f"{SYSTEM}\n"
        for h in history[-6:]:
            p += f"{'User' if h['role'] == 'user' else 'Teto'}: {h['content']}\n"
        p += "Teto:"
    return p


def _extract(data):
    if isinstance(data, list) and data:
        entry = data[0]
        return entry.get("generated_text", "") if isinstance(entry, dict) else str(entry)
    if isinstance(data, dict):
        return data.get("generated_text", "")
    return None
