import sys
import os
import threading
import socket
import subprocess
import time

import requests
from gi.repository import GLib

from desktop_pet import config
from desktop_pet.models import model
from desktop_pet.log import log
from desktop_pet import platform

# ── System prompts ────────────────────────────────────────

SYSTEM = model.SYSTEM_PROMPT

TOOL_SYSTEM = (
    "You have REAL abilities on the user's computer. You can actually do these things:\n"
    "- list_files path=<dir> — list files in a directory\n"
    "- read_file path=<file> — read a text file\n"
    "- run_command command=<shell> — run any system command\n"
    "- write_file path=<file> content=<text> — write/create a file\n"
    "- open_url url=<url> — open a URL in the browser\n"
    "- screenshot — capture the screen (then you can see and describe it)\n"
    "CRITICAL: NEVER say you can't do something or that you're just a virtual assistant. "
    "You have real computer control. Use a tool to do it.\n"
    "To use a tool, respond with EXACTLY one line starting with TOOL:\n"
    "TOOL: <name> | <key>=<value> | ...\n"
    "Do NOT wrap it in brackets, markdown, or extra text.\n"
    "When you see [Resultado de <tool>: ...] in the conversation, that means the "
    "tool already ran successfully. Respond naturally about what happened.\n"
    "NEVER make up file contents. Always use a tool to check.\n"
    "NEVER guess about the user's computer. Use run_command instead."
)


def ask(message, history=None, callback=None, tool_context=None, image_base64=None):
    if not history:
        history = []
    p = config.load().get("ai_provider", config.PROVIDER_AUTO)
    return ask_with_provider(p, message, history, callback, tool_context, image_base64)


def ask_with_provider(provider, message, history, callback=None, tool_context=None, image_base64=None):
    if not history:
        history = []
    if callback is None:
        return _run_provider(provider, message, history, tool_context, image_base64)
    thread = threading.Thread(
        target=lambda: GLib.idle_add(callback, _run_provider(provider, message, history, tool_context, image_base64)),
        daemon=True,
    )
    thread.start()


def _run_provider(provider, message, history, tool_context=None, image_base64=None):
    msg = message
    if tool_context:
        msg = f"{message}\n\n[Ferramenta usada: {tool_context}]"

    if provider == config.PROVIDER_AUTO:
        reply = _ask_groq(msg, history, image_base64)
        if reply:
            log("Groq → %s", reply)
            return reply
        reply = _ask_gemini(msg, history, image_base64)
        if reply:
            if not reply.startswith("TOOL:"):
                log("Gemini → %s", reply)
            return reply
        reply = _ask_hf(msg, history)
        if reply:
            log("HuggingFace → %s", reply)
            return reply
        f = model.phrases.get_fallback(msg, history)
        log("Frases prontas → %s", f)
        return f

    if provider == config.PROVIDER_OLLAMA:
        reply = _ask_ollama(msg, history)
        if reply:
            log("Ollama → %s", reply)
            return reply
        f = model.phrases.get_fallback(msg, history)
        log("Frases prontas → %s", f)
        return f

    if provider == config.PROVIDER_HF:
        reply = _ask_hf(msg, history)
        if reply:
            log("HuggingFace → %s", reply)
            return reply
        key = config.load().get("hf_token", "")
        if not key:
            return "Hmm, você selecionou HuggingFace mas não configurou o token! 🛡️\nVá no menu em Configurações > Inteligência > Configurar HuggingFace... pra pegar um token grátis em huggingface.co/settings/tokens"
        return "HuggingFace não respondeu. Pode ser cota esgotada ou token inválido."

    if provider == "gemini":
        reply = _ask_gemini(msg, history, image_base64)
        if reply:
            if not reply.startswith("TOOL:"):
                log("Gemini → %s", reply)
            return reply
        key = config.load().get("gemini_key", "")
        if not key:
            return "Hmm, você selecionou Gemini mas não configurou a chave! 🛡️\nVá no menu e clique em **Configurar Gemini** pra pegar uma chave grátis!"
        return "Gemini não respondeu. Pode ser cota esgotada ou chave inválida. Tenta outra chave em Configurar Gemini."

    if provider == config.PROVIDER_GROQ:
        reply = _ask_groq(msg, history, image_base64)
        if reply:
            log("Groq → %s", reply)
            return reply
        key = config.load().get("groq_key", "")
        if not key:
            return "Hmm, você selecionou Groq mas não configurou a chave! 🛡️\nVá no menu em **Configurar Groq...** pra pegar uma chave grátis!"
        return "Groq não respondeu. Pode ser cota esgotada ou chave inválida."

    f = model.phrases.get_fallback(msg, history)
    log("Frases prontas → %s", f)
    return f


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
    cfg = config.load()
    sys_msg = SYSTEM
    user_name = cfg.get("user_name", "").strip()
    user_bio = cfg.get("user_bio", "").strip()
    if user_name:
        sys_msg += f"\n\nO usuário se chama {user_name}. SEMPRE o trate por {user_name} e nunca se esqueça do nome dele(a)."
    if user_bio:
        sys_msg += f"\nInformações sobre o usuário: {user_bio}"
    if any(cfg.get(k, False) for k in config.TOOL_KEYS):
        sys_msg += "\n\n" + TOOL_SYSTEM
    msgs = [{"role": "system", "content": sys_msg}]
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
    cfg = config.load()
    preferred = cfg.get("ollama_model", "").strip()
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return None
        models = resp.json().get("models", [])
        if not models:
            return None

        if preferred:
            for m in models:
                if m["name"] == preferred:
                    return preferred

        sorted_models = sorted(models, key=lambda m: m.get("size", 0), reverse=True)
        return sorted_models[0]["name"]
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
                return text
    except requests.RequestException as e:
        log("Ollama error: %s", e)
    return None


# ─── Hugging Face ─────────────────────────────────────────


def _ask_hf(message, history):
    hf_token = config.load().get("hf_token", "")
    if not hf_token:
        return None

    models = [
        "katanemo/Arch-Router-1.5B",
    ]

    msgs = _build_messages(history, message)
    chat_msgs = [m for m in msgs if m["role"] != "system"]
    sys_prompt = next((m["content"] for m in msgs if m["role"] == "system"), "")

    for model_id in models:
        try:
            body = {
                "model": model_id,
                "messages": [{"role": "system", "content": sys_prompt}] + chat_msgs,
                "max_tokens": 200,
                "temperature": 0.8,
            }
            resp = requests.post(
                "https://router.huggingface.co/hf-inference/v1/chat/completions",
                json=body,
                timeout=15,
                headers={
                    "Authorization": f"Bearer {hf_token}",
                    "User-Agent": "mate-helper/1.0",
                },
            )
        except requests.RequestException as e:
            log("HF %s error: %s", model_id, e)
            continue

        if resp.status_code == 503:
            log("HF %s loading (503)", model_id)
            continue
        if resp.status_code == 401:
            log("HF token inválido (401)")
            return None
        if resp.status_code != 200:
            log("HF %s error %s: %s", model_id, resp.status_code, resp.text[:100])
            continue

        try:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text:
                return text
        except (KeyError, IndexError, ValueError) as e:
            log("HF %s parse error: %s", model_id, e)
            continue

    return None


# ─── Gemini ────────────────────────────────────────────────

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def _ask_gemini(message, history, image_base64=None):
    key = config.load().get("gemini_key", "")
    if not key:
        return None

    if not _resolve("generativelanguage.googleapis.com"):
        log("Gemini domain unreachable")
        return None

    contents = []
    for h in history[-8:]:
        role = "user" if h["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h["content"]}]})

    if image_base64:
        user_part = {
            "parts": [
                {"inlineData": {"mimeType": "image/png", "data": image_base64}},
                {"text": message},
            ]
        }
    else:
        user_part = {"parts": [{"text": message}]}
    contents.append({"role": "user", **user_part})

    cfg = config.load()
    sys_msg = SYSTEM
    if any(cfg.get(k, False) for k in config.TOOL_KEYS):
        sys_msg += "\n\n" + TOOL_SYSTEM

    for model in GEMINI_MODELS:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                json={
                    "contents": contents,
                    "systemInstruction": {"parts": [{"text": sys_msg}]},
                    "generationConfig": {
                        "maxOutputTokens": 200,
                        "temperature": 0.8,
                    },
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        return text
            elif resp.status_code == 429:
                continue
            elif resp.status_code == 403:
                return "Sua chave Gemini parece inválida ou expirou. Vá em Configurar Gemini e cole uma chave nova grátis em https://aistudio.google.com/apikey"
            elif resp.status_code == 404:
                continue
            else:
                continue
        except requests.RequestException as e:
            log("Gemini request failed: %s", e)
            continue

    return None


# ─── Groq ──────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


def _ask_groq(message, history, image_base64=None):
    key = config.load().get("groq_key", "")
    if not key:
        return None

    msgs = _build_messages(history, message)
    chat_msgs = [m for m in msgs if m["role"] != "system"]
    sys_prompt = next((m["content"] for m in msgs if m["role"] == "system"), "")

    if image_base64:
        model = GROQ_VISION_MODEL
        max_tokens = 300
        for i, m in enumerate(chat_msgs):
            if m["role"] == "user":
                chat_msgs[i] = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": m["content"]},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                    ],
                }
                break
    else:
        model = GROQ_MODEL
        max_tokens = 200

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "system", "content": sys_prompt}] + chat_msgs,
                "max_tokens": max_tokens,
                "temperature": 0.8,
            },
            headers={"Authorization": f"Bearer {key}"},
            timeout=15,
        )
        if resp.status_code == 200:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            return text
        elif resp.status_code == 429:
            log("Groq: cota esgotada (429)")
            return None
        elif resp.status_code == 401:
            log("Groq: chave inválida (401)")
            return None
        else:
            log("Groq error %s: %s", resp.status_code, resp.text[:200])
            return None
    except requests.RequestException as e:
        log("Groq request failed: %s", e)
        return None


def transcribe(audio_path):
    key = config.load().get("groq_key", "")
    if not key:
        return None
    if not audio_path or not os.path.exists(audio_path):
        return None
    try:
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            resp = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                files=files,
                data={"model": "whisper-large-v3-turbo", "language": "pt"},
                timeout=30,
            )
        os.unlink(audio_path)
        if resp.status_code == 200:
            text = resp.json().get("text", "").strip()
            return text if text else None
        elif resp.status_code == 429:
            log("Groq Whisper: cota esgotada")
            return None
        else:
            log("Groq Whisper error %s: %s", resp.status_code, resp.text[:200])
            return None
    except requests.RequestException as e:
        log("Groq Whisper request failed: %s", e)
        return None
    except OSError as e:
        log("Erro ao ler áudio: %s", e)
        return None


# ─── Ollama auto-management ────────────────────────────────

_ollama_started_by_us = False


def ollama_ensure_running():
    global _ollama_started_by_us

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            return True
    except requests.RequestException:
        pass

    if not platform.find_exe("ollama"):
        log("Ollama not installed")
        return False

    log("Starting Ollama...")
    try:
        if platform.IS_WINDOWS:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        _ollama_started_by_us = True
        for _ in range(10):
            time.sleep(1)
            try:
                resp = requests.get("http://localhost:11434/api/tags", timeout=2)
                if resp.status_code == 200:
                    log("Ollama started!")
                    return True
            except requests.RequestException:
                pass
    except Exception as e:
        log("Failed to start Ollama: %s", e)

    return False


def ollama_stop():
    global _ollama_started_by_us
    if not _ollama_started_by_us:
        return
    log("Stopping Ollama...")
    platform.kill_process("ollama.exe" if platform.IS_WINDOWS else "ollama")
    _ollama_started_by_us = False



