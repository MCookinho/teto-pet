import json
import urllib.request
import urllib.error

from teto_pet import phrases

HF_MODEL = "HuggingFaceH4/zephyr-7b-beta"
HF_API = f"https://api-inference.huggingface.co/models/{HF_MODEL}"


def ask(message, history=None):
    if not history:
        history = []

    reply = _ask_huggingface(message, history)
    if reply:
        return reply

    return _ask_fallback(message)


def _ask_huggingface(message, history):
    system = (
        "You are Kasane Teto, an energetic and playful UTAU vocaloid. "
        "Keep answers short, cute, and in Portuguese. Use emoticons. "
        "You are a desktop companion and best friend."
    )
    prompt = f"{system}\n"
    for h in history[-6:]:
        role = h["role"]
        prompt += f"{'User' if role == 'user' else 'Teto'}: {h['content']}\n"
    prompt += "Teto:"

    payload = json.dumps({
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 60,
            "temperature": 0.8,
            "top_p": 0.9,
            "do_sample": True,
        },
    }).encode()

    req = urllib.request.Request(
        HF_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            if isinstance(data, list):
                text = data[0].get("generated_text", "")
                if text:
                    after = text.split("Teto:")[-1].strip()
                    return after
            elif isinstance(data, dict):
                return data.get("generated_text", "")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError,
            json.JSONDecodeError, KeyError):
        pass

    return None


def _ask_fallback(message):
    return phrases.get_fallback(message)
