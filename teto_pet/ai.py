import sys
import threading
import socket

import requests
from gi.repository import GLib

from teto_pet import phrases, config

SYSTEM = (
    "You are Kasane Teto, an energetic and playful UTAU vocaloid. "
    "Keep answers short (1-2 sentences), cute, and in Portuguese (Brazilian). "
    "Use emoticons like ^_^, :3, >_<, etc. "
    "You are a desktop companion and best friend."
)


def ask(message, history=None, callback=None):
    if not history:
        history = []
    p = config.load().get("ai_provider", config.PROVIDER_AUTO)
    return ask_with_provider(p, message, history, callback)


def ask_with_provider(provider, message, history, callback=None):
    if not history:
        history = []
    if callback is None:
        return _run_provider(provider, message, history)
    thread = threading.Thread(
        target=lambda: GLib.idle_add(callback, _run_provider(provider, message, history)),
        daemon=True,
    )
    thread.start()


def _run_provider(provider, message, history):
    if provider == config.PROVIDER_AUTO:
        reply = _ask_ollama(message, history)
        if reply:
            return reply
        reply = _ask_hf(message, history)
        if reply:
            return reply
        reply = _ask_gemini(message, history)
        if reply:
            return reply
        print("[teto-pet] All providers failed, using phrases", file=sys.stderr)
        return phrases.get_fallback(message)

    if provider == config.PROVIDER_OLLAMA:
        reply = _ask_ollama(message, history)
        if reply:
            return reply
        return phrases.get_fallback(message)

    if provider == config.PROVIDER_HF:
        reply = _ask_hf(message, history)
        if reply:
            return reply
        return phrases.get_fallback(message)

    if provider == "gemini":
        reply = _ask_gemini(message, history)
        if reply:
            return reply
        return phrases.get_fallback(message)

    return phrases.get_fallback(message)


def _resolve(host, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return True
    except OSError:
        pass
    try:
        resp = requests.get(
            f"https://cloudflare-dns.com/dns-query?name={host}&type=A",
            headers={"Accept": "application/dns-json"},
            timeout=timeout,
        )
        if resp.status_code == 200:
            for a in resp.json().get("Answer", []):
                if a.get("type") == 1:
                    return True
    except requests.RequestException:
        pass
    return False


def _build_messages(history, message):
    msgs = [{"role": "system", "content": SYSTEM}]
    for h in history[-8:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": message})
    return msgs


# ─── Ollama ─────────────────────────────────────────────


def _ask_ollama(message, history):
    model = _ollama_model()
    if not model:
        return None

    msgs = _build_messages(history, message)
    reply = _ollama_chat(model, msgs)
    return reply or None


def _ollama_model():
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return None
        models = resp.json().get("models", [])
        if not models:
            return None
        model_names = sorted(m["name"] for m in models)
        chosen = model_names[0]
        return chosen
    except requests.RequestException:
        return None


def _ollama_chat(model, messages):
    try:
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages, "stream": False,
                  "options": {"num_predict": 200, "temperature": 0.8}},
            timeout=30,
        )
        if resp.status_code == 200:
            text = resp.json().get("message", {}).get("content", "")
            if text:
                for prefix in ("Teto:", "teto:", "Assistente:", "assistente:"):
                    if text.startswith(prefix):
                        text = text[len(prefix):]
                text = text.strip()
                print(f"[teto-pet] Ollama: {text[:60]}", file=sys.stderr)
                return text
    except requests.RequestException as e:
        print(f"[teto-pet] Ollama error: {e}", file=sys.stderr)
    return None


# ─── Hugging Face ─────────────────────────────────────────


def _ask_hf(message, history):
    if not _resolve("api-inference.huggingface.co"):
        print("[teto-pet] HuggingFace domain unreachable, skipping", file=sys.stderr)
        return None

    models = [
        ("HuggingFaceH4/zephyr-7b-beta", "zephyr"),
        ("microsoft/DialoGPT-medium", "default"),
    ]

    for model_id, fmt in models:
        prompt = _build_prompt(fmt, message, history)
        try:
            resp = requests.post(
                f"https://api-inference.huggingface.co/models/{model_id}",
                json={"inputs": prompt, "parameters": _params(fmt)},
                timeout=10,
                headers={"User-Agent": "teto-pet/1.0"},
            )
        except requests.RequestException as e:
            print(f"[teto-pet] HF {model_id} error: {e}", file=sys.stderr)
            continue

        if resp.status_code == 503:
            print(f"[teto-pet] HF {model_id} loading (503)", file=sys.stderr)
            continue
        if resp.status_code != 200:
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


# ─── Gemini ────────────────────────────────────────────────


def _ask_gemini(message, history):
    key = config.load().get("gemini_key", "")
    if not key:
        return None

    if not _resolve("generativelanguage.googleapis.com"):
        print("[teto-pet] Gemini domain unreachable", file=sys.stderr)
        return None

    contents = []
    for h in history[-8:]:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["content"]}]})
    contents.append({"role": "user", "parts": [{"text": message}]})

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
            json={
                "contents": contents,
                "systemInstruction": {"parts": [{"text": SYSTEM}]},
                "generationConfig": {
                    "maxOutputTokens": 200,
                    "temperature": 0.8,
                },
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    print(f"[teto-pet] Gemini: {text[:60]}", file=sys.stderr)
                    return text
        else:
            print(f"[teto-pet] Gemini error {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
    except requests.RequestException as e:
        print(f"[teto-pet] Gemini error: {e}", file=sys.stderr)

    return None


# ─── Shared helpers ────────────────────────────────────────


def _params(fmt):
    base = {"max_new_tokens": 60, "temperature": 0.8, "top_p": 0.9, "do_sample": True}
    if fmt == "default":
        base["max_new_tokens"] = 80
    return base


def _build_prompt(fmt, message, history):
    if fmt == "zephyr":
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
