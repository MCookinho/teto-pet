import os
import sys
import subprocess
import tempfile
import base64
import io
import array

from PIL import ImageGrab

IS_WINDOWS = sys.platform == "win32"


def config_dir():
    if IS_WINDOWS:
        return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "teto-pet")
    return os.path.expanduser("~/.config/teto-pet")


def cache_dir():
    if IS_WINDOWS:
        return os.path.join(os.environ.get("TEMP", os.path.expanduser("~")), "mate-helper")
    return os.path.expanduser("~/.cache/mate-helper")


def history_dir():
    return os.path.join(config_dir(), "history")


def ptt_socket_path():
    return os.path.join(cache_dir(), "ptt.sock")


def ptt_helper_path():
    if IS_WINDOWS:
        return os.path.join(config_dir(), "ptt_helper.ps1")
    return os.path.expanduser("~/.local/bin/mate-helper-ptt")


def find_exe(name):
    try:
        if IS_WINDOWS:
            subprocess.run(["where", name], capture_output=True, check=True, timeout=5)
        else:
            subprocess.run(["which", name], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def kill_process(name):
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/f", "/im", name], capture_output=True)
    else:
        subprocess.run(["pkill", name], capture_output=True)


def run_shell(command, timeout=30):
    if IS_WINDOWS:
        return subprocess.run(
            ["cmd", "/c", command],
            capture_output=True, timeout=timeout, text=True,
        )
    return subprocess.run(
        ["bash", "-c", command],
        capture_output=True, timeout=timeout, text=True,
    )


def open_url(url):
    if IS_WINDOWS:
        try:
            os.startfile(url)
        except Exception:
            import webbrowser
            webbrowser.open(url)
    else:
        subprocess.run(["xdg-open", url], capture_output=True, timeout=5)


def screenshot():
    try:
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass

    if not IS_WINDOWS:
        for cmd_name, cmd_args in [
            ("gnome-screenshot", ["gnome-screenshot", "-f"]),
            ("import", ["import", "-window", "root"]),
            ("spectacle", ["spectacle", "-b", "-n", "-o"]),
        ]:
            try:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    tmp = f.name
                subprocess.run(cmd_args + [tmp], capture_output=True, timeout=5)
                if os.path.getsize(tmp) > 0:
                    with open(tmp, "rb") as f:
                        data = base64.b64encode(f.read()).decode()
                    os.unlink(tmp)
                    return data
                os.unlink(tmp)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

    return "Não consegui capturar a tela."


def list_audio_devices():
    if IS_WINDOWS:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxInputChannels"] > 0:
                    devices.append({"id": str(i), "name": info["name"]})
            p.terminate()
            return devices
        except ImportError:
            return []
    else:
        try:
            result = subprocess.run(
                ["pactl", "list", "sources", "short"],
                capture_output=True, text=True, timeout=5,
            )
            mics = []
            for line in result.stdout.strip().split("\n"):
                if "monitor" not in line and line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        mics.append({"id": parts[1], "name": parts[1]})
            return mics
        except Exception:
            return []


def list_sinks():
    if IS_WINDOWS:
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxOutputChannels"] > 0:
                    devices.append({"id": str(i), "name": info["name"]})
            p.terminate()
            return devices
        except ImportError:
            return []
    else:
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
                        devices.append({"id": parts[1], "name": parts[1]})
            return devices
        except Exception:
            return []


def record_mic(device=None, duration=5, stop_event=None):
    if IS_WINDOWS:
        return _record_mic_windows(device, duration, stop_event)
    return _record_mic_linux(device, duration, stop_event)


def _record_mic_windows(device, duration, stop_event):
    try:
        import pyaudio
        import wave

        p = pyaudio.PyAudio()
        device_index = None
        if device:
            try:
                device_index = int(device)
            except ValueError:
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    if device in info["name"]:
                        device_index = i
                        break

        fmt = pyaudio.paInt16
        channels = 1
        rate = 16000
        chunk = 1024

        stream = p.open(
            format=fmt, channels=channels, rate=rate,
            input=True, input_device_index=device_index,
            frames_per_buffer=chunk,
        )

        frames = []
        total_chunks = int(rate / chunk * duration)
        for _ in range(total_chunks):
            if stop_event and stop_event.is_set():
                break
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        if not frames:
            p.terminate()
            return "Erro: áudio muito curto"

        all_data = b"".join(frames)
        samples = array.array('h')
        samples.frombytes(all_data[:200000])
        if samples:
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            if rms < 100:
                p.terminate()
                return "Erro: áudio muito baixo (silêncio)"

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(fmt))
            wf.setframerate(rate)
            wf.writeframes(all_data)

        p.terminate()
        return tmp.name
    except ImportError:
        return "Erro: pyaudio não instalado"
    except Exception as e:
        return f"Erro ao capturar áudio: {e}"


def _record_mic_linux(device, duration, stop_event):
    raw = None
    try:
        if not device:
            mics = list_audio_devices()
            if not mics:
                return "Erro: nenhum microfone encontrado"
            device = mics[0]["id"]

        raw = tempfile.NamedTemporaryFile(suffix=".raw", delete=False)
        raw.close()

        fh = open(raw.name, "wb")
        proc = subprocess.Popen(
            ["parec", "--device", device, "--format=s16le",
             "--rate=16000", "--channels=1", "--raw"],
            stdout=fh, stderr=subprocess.DEVNULL,
        )

        if stop_event:
            stop_event.wait(timeout=duration)
            proc.kill()
        else:
            try:
                proc.wait(timeout=duration)
            except subprocess.TimeoutExpired:
                proc.kill()
        proc.wait()
        fh.close()

        if not os.path.exists(raw.name) or os.path.getsize(raw.name) < 100:
            os.unlink(raw.name)
            return "Erro: áudio muito curto"

        try:
            import webrtcvad
            data = open(raw.name, "rb").read()
            vad = webrtcvad.Vad(2)
            samples = array.array('h')
            samples.frombytes(data)
            frame_len = 480
            total = len(samples) // frame_len
            if total > 0:
                speech_frames = 0
                for i in range(total):
                    frame = samples[i * frame_len:(i + 1) * frame_len].tobytes()
                    if vad.is_speech(frame, 16000):
                        speech_frames += 1
                ratio = speech_frames / total
                if ratio < 0.05:
                    os.unlink(raw.name)
                    return "Erro: áudio parece ruído (VAD)"
        except ImportError:
            pass
        except Exception:
            pass

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        ret = subprocess.run(
            ["ffmpeg", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1",
             "-i", raw.name, tmp.name],
            capture_output=True, timeout=10,
        )
        os.unlink(raw.name)
        if ret.returncode != 0 or os.path.getsize(tmp.name) < 100:
            os.unlink(tmp.name)
            return "Erro: falha ao converter áudio para WAV"
        return tmp.name

    except (FileNotFoundError, OSError) as e:
        if raw and os.path.exists(raw.name):
            os.unlink(raw.name)
        return f"Erro ao capturar áudio: {e}"


def record_desktop_audio(duration=8):
    if IS_WINDOWS:
        return _record_desktop_windows(duration)
    return _record_desktop_linux(duration)


def _record_desktop_windows(duration):
    try:
        import pyaudio
        import wave

        p = pyaudio.PyAudio()
        loopback_index = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0 and "loopback" in info["name"].lower():
                loopback_index = i
                break

        if loopback_index is None:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info["maxOutputChannels"] > 0:
                    loopback_index = i
                    break

        if loopback_index is None:
            p.terminate()
            return "Erro: nenhum dispositivo de áudio encontrado"

        fmt = pyaudio.paInt16
        channels = 1
        rate = 16000
        chunk = 1024

        stream = p.open(
            format=fmt, channels=channels, rate=rate,
            input=True, input_device_index=loopback_index,
            frames_per_buffer=chunk,
        )

        frames = []
        total_chunks = int(rate / chunk * duration)
        for _ in range(total_chunks):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        if not frames:
            p.terminate()
            return "Erro: áudio capturado muito curto"

        all_data = b"".join(frames)
        samples = array.array('h')
        samples.frombytes(all_data[:200000])
        if samples:
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            if rms < 100:
                p.terminate()
                return "Erro: áudio muito baixo (silêncio)"

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(fmt))
            wf.setframerate(rate)
            wf.writeframes(all_data)

        p.terminate()
        return tmp.name
    except ImportError:
        return "Erro: pyaudio não instalado"
    except Exception as e:
        return f"Erro ao capturar áudio: {e}"


def _record_desktop_linux(duration):
    raw = None
    try:
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True, text=True, timeout=5,
        )
        monitors = []
        for line in result.stdout.strip().split("\n"):
            if "monitor" in line:
                parts = line.split()
                if len(parts) >= 2:
                    monitors.append((parts[1], "SUSPENDED" not in line))

        if not monitors:
            return "Erro: nenhuma fonte de áudio monitor encontrada"

        active = [m for m in monitors if m[1]]
        source = active[0][0] if active else monitors[0][0]

        raw = tempfile.NamedTemporaryFile(suffix=".raw", delete=False)
        raw.close()
        try:
            subprocess.run(
                ["timeout", str(duration + 1),
                 "parec", "--device", source, "--format=s16le",
                 "--rate=16000", "--channels=1", "--raw"],
                stdout=open(raw.name, "wb"),
                stderr=subprocess.DEVNULL,
                timeout=duration + 5,
            )
        except subprocess.TimeoutExpired:
            pass

        if not os.path.exists(raw.name) or os.path.getsize(raw.name) < 100:
            os.unlink(raw.name)
            return "Erro: áudio capturado muito curto"

        try:
            data = open(raw.name, "rb").read()
            samples = array.array('h')
            samples.frombytes(data[:200000])
            if samples:
                rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
                if rms < 100:
                    os.unlink(raw.name)
                    return "Erro: áudio muito baixo (silêncio)"
        except Exception:
            pass

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        ret = subprocess.run(
            ["ffmpeg", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1",
             "-i", raw.name, tmp.name],
            capture_output=True, timeout=10,
        )
        os.unlink(raw.name)
        if ret.returncode != 0 or os.path.getsize(tmp.name) < 100:
            os.unlink(tmp.name)
            return "Erro: falha ao converter áudio para WAV"
        return tmp.name

    except (FileNotFoundError, OSError) as e:
        if raw and os.path.exists(raw.name):
            os.unlink(raw.name)
        return f"Erro ao capturar áudio: {e}"

