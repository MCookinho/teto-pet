import os
import subprocess
import tempfile
import threading

from desktop_pet.log import log

TTS_PROVIDER_AUTO = "auto"
TTS_PROVIDER_FISH = "fish_audio"
TTS_PROVIDER_EDGE = "edge_tts"
TTS_PROVIDER_PYTTS = "pyttsx3"

TTS_PROVIDERS = [
    TTS_PROVIDER_AUTO,
    TTS_PROVIDER_FISH,
    TTS_PROVIDER_EDGE,
    TTS_PROVIDER_PYTTS,
]

FISH_API_URL = "https://api.fish.audio/v1/tts"


def _provider_order(provider):
    if provider == TTS_PROVIDER_AUTO:
        return [TTS_PROVIDER_FISH, TTS_PROVIDER_EDGE, TTS_PROVIDER_PYTTS]
    return [provider]


def list_audio_devices():
    try:
        result = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            capture_output=True, text=True, timeout=2,
        )
        devices = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[1]
                    desc = _get_sink_description(name)
                    devices.append({"id": name, "description": desc or name})
        return devices
    except Exception as e:
        log("tts: falha ao listar dispositivos: %s", e)
        return []


def _get_sink_description(name):
    try:
        result = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True, text=True, timeout=2,
        )
        current_name = None
        for line in result.stdout.split("\n"):
            if "Name:" in line and name in line:
                current_name = name
            if current_name and "Description:" in line:
                return line.split(":", 1)[1].strip()
        return None
    except Exception:
        return None


def _play_audio(path, device=None):
    env = os.environ.copy()
    if device:
        env["PULSE_SINK"] = device
    subprocess.run(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=env, timeout=30,
    )


def _speak_fish(text, reference_id, api_key, device):
    if not api_key:
        return False
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": "s2-pro",
        }
        data = {"text": text, "format": "wav"}
        if reference_id:
            data["reference_id"] = reference_id
        resp = requests.post(
            FISH_API_URL, headers=headers, json=data, stream=True, timeout=30
        )
        if resp.status_code != 200:
            log("tts: fish audio erro %s: %s", resp.status_code, resp.text[:200])
            return False
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
            tmp = f.name
        _play_audio(tmp, device)
        os.unlink(tmp)
        return True
    except ImportError:
        log("tts: requests nao instalado")
        return False
    except Exception as e:
        log("tts: fish audio erro: %s", e)
        return False


def _speak_edge(text, voice, device):
    if not voice:
        return False
    try:
        import edge_tts
        import asyncio

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name

        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            await asyncio.wait_for(communicate.save(tmp), timeout=15)

        asyncio.run(_run())
        _play_audio(tmp, device)
        os.unlink(tmp)
        return True
    except ImportError:
        log("tts: edge-tts nao instalado")
        return False
    except asyncio.TimeoutError:
        log("tts: edge-tts timeout")
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    except Exception as e:
        log("tts: edge-tts erro: %s", e)
        return False


def _speak_pyttsx3(text, voice):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        if voice:
            voices = engine.getProperty("voices")
            for v in voices:
                if voice in v.id.lower() or voice in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
        engine.say(text)
        engine.runAndWait()
        return True
    except ImportError:
        log("tts: pyttsx3 nao instalado")
        return False
    except Exception as e:
        log("tts: pyttsx3 erro: %s", e)
        return False


def speak(text, provider, voice_config, api_key=None, device=None):
    for prov in _provider_order(provider):
        if prov == TTS_PROVIDER_FISH:
            if _speak_fish(text, voice_config.get("fish_audio", ""), api_key, device):
                return True
        elif prov == TTS_PROVIDER_EDGE:
            if _speak_edge(text, voice_config.get("edge_tts", ""), device):
                return True
        elif prov == TTS_PROVIDER_PYTTS:
            if _speak_pyttsx3(text, voice_config.get("pyttsx3", "")):
                return True
    return False


def speak_async(text, provider, voice_config, api_key=None, device=None):
    threading.Thread(
        target=speak,
        args=(text, provider, voice_config, api_key, device),
        daemon=True,
    ).start()
