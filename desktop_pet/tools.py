import os
import io
import re
import shlex
import base64
import array
import subprocess
import tempfile

from PIL import ImageGrab

MAX_FILE_CHARS = 2000
MAX_OUTPUT_CHARS = 3000
CMD_TIMEOUT = 30

DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\s+/\s*$',
    r'\brm\s+-rf\s+--no-preserve-root\b',
    r'\bdd\s+if=',
    r'\bmkfs\.',
    r'\bmkswap\b',
    r'\b:\(\)\s*\{',
    r'\bchmod\s+777\s+/',
    r'\b>(\s+/dev/\w+)',
    r'\bshred\b',
]
DANGEROUS_RE = re.compile('|'.join(DANGEROUS_PATTERNS))


# ─── Funções-ferramenta ─────────────────────────────────


def read_file(path):
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return f"Erro: arquivo não encontrado: {path}"
    if not os.path.isfile(expanded):
        return f"Erro: não é um arquivo: {path}"
    try:
        with open(expanded, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        size = len(content)
        if size > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + f"\n\n... (truncado, {size} chars)"
        return content
    except PermissionError:
        return f"Sem permissão para ler {path}"
    except Exception as e:
        return f"Erro ao ler {path}: {e}"


MAX_LIST_ITEMS = 60


def list_files(path="~"):
    """Lista arquivos/pastas em um diretório (máx 60 itens)."""
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return f"Erro: pasta não encontrada: {path}"
    try:
        items = []
        for item in sorted(os.listdir(expanded)):
            full = os.path.join(expanded, item)
            suffix = "/" if os.path.isdir(full) else ""
            items.append(f"{item}{suffix}")
        size = len(items)
        if size > MAX_LIST_ITEMS:
            items = items[:MAX_LIST_ITEMS]
            items.append(f"... e mais {size - MAX_LIST_ITEMS} itens")
        return "\n".join(items)
    except PermissionError:
        return f"Sem permissão para listar {path}"
    except Exception as e:
        return f"Erro ao listar {path}: {e}"


def screenshot():
    # Try PIL (X11)
    try:
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass

    # Try grim (Wayland wlroots)
    try:
        result = subprocess.run(
            ["grim", "-"], capture_output=True, timeout=5
        )
        if result.returncode == 0:
            return base64.b64encode(result.stdout).decode()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try gnome-screenshot (GNOME Wayland)
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        subprocess.run(
            ["gnome-screenshot", "-f", tmp], capture_output=True, timeout=5
        )
        if os.path.getsize(tmp) > 0:
            with open(tmp, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            os.unlink(tmp)
            return data
        os.unlink(tmp)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try import (ImageMagick, X11)
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        subprocess.run(
            ["import", "-window", "root", tmp], capture_output=True, timeout=5
        )
        if os.path.getsize(tmp) > 0:
            with open(tmp, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            os.unlink(tmp)
            return data
        os.unlink(tmp)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try spectacle (KDE)
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp = f.name
        subprocess.run(
            ["spectacle", "-b", "-n", "-o", tmp], capture_output=True, timeout=5
        )
        if os.path.getsize(tmp) > 0:
            with open(tmp, "rb") as f:
                data = base64.b64encode(f.read()).decode()
            os.unlink(tmp)
            return data
        os.unlink(tmp)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "Não consegui capturar a tela. Tenta instalar: grim (Wayland) ou gnome-screenshot"


def run_command(command):
    if DANGEROUS_RE.search(command):
        return "Comando bloqueado por segurança (parece destrutivo demais)"

    expanded = os.path.expanduser(command)
    try:
        result = subprocess.run(
            ["bash", "-c", expanded],
            capture_output=True,
            timeout=CMD_TIMEOUT,
            text=True,
        )
        out = (result.stdout or "") + (result.stderr or "")
        if not out.strip():
            out = f"(ok, exit code {result.returncode})"
        if len(out) > MAX_OUTPUT_CHARS:
            out = out[:MAX_OUTPUT_CHARS] + f"\n\n... (truncado, {len(out)} chars)"
        return out.strip()
    except subprocess.TimeoutExpired:
        return "Comando excedeu o tempo limite (30s)"
    except OSError as e:
        return f"Erro ao executar: {e}"


def write_file(path, content):
    expanded = os.path.expanduser(path)
    parent = os.path.dirname(expanded)
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as e:
            return f"Não consegui criar o diretório {parent}: {e}"
    try:
        with open(expanded, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Arquivo salvo em {path} ({len(content)} chars)"
    except OSError as e:
        return f"Erro ao escrever {path}: {e}"


def open_url(url):
    import subprocess
    try:
        subprocess.run(["xdg-open", url], capture_output=True, timeout=5)
        return f"URL aberta: {url}"
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"Erro ao abrir URL: {e}"


def list_mic_sources():
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
                    mics.append(parts[1])
        return mics
    except Exception:
        return []


def listen_mic(device=None, duration=5, stop_event=None):
    raw = None
    try:
        if not device:
            mics = list_mic_sources()
            if not mics:
                return "Erro: nenhum microfone encontrado"
            device = mics[0]
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
        # Detecta silêncio — evita enviar ruído ambiente pro Whisper
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


def listen(duration=8):
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

        # Detecta silêncio — se o RMS for muito baixo, não vale enviar pro Whisper
        try:
            data = open(raw.name, "rb").read()
            samples = array.array('h')
            samples.frombytes(data[:200000])  # até ~100k samples (6s de 16kHz)
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


TOOLS = {
    "read_file": {
        "name": "read_file",
        "description": "Lê o conteúdo de um arquivo de texto",
        "execute": read_file,
        "parameters": {"path": "caminho do arquivo"},
    },
    "list_files": {
        "name": "list_files",
        "description": "Lista arquivos e pastas em um diretório",
        "execute": list_files,
        "parameters": {"path": "caminho da pasta (padrão .)"},
    },
    "screenshot": {
        "name": "screenshot",
        "description": "Tira um print da tela do computador",
        "execute": screenshot,
        "parameters": {},
    },
    "run_command": {
        "name": "run_command",
        "description": "Executa um comando bash no computador",
        "execute": run_command,
        "parameters": {"command": "comando bash para executar"},
    },
    "write_file": {
        "name": "write_file",
        "description": "Escreve conteúdo em um arquivo (cria se não existir)",
        "execute": write_file,
        "parameters": {"path": "caminho do arquivo", "content": "conteúdo a escrever"},
    },
    "open_url": {
        "name": "open_url",
        "description": "Abre uma URL no navegador padrão",
        "execute": open_url,
        "parameters": {"url": "URL para abrir"},
    },
    "listen": {
        "name": "listen",
        "description": "Escuta os sons do desktop (música, chamadas, sons em geral) por alguns segundos e retorna o arquivo de áudio",
        "execute": listen,
        "parameters": {},
    },
}

TOOL_KEYWORDS = {
    "read_file": [
        "ler", "abrir", "mostrar", "ver", "exibir", "pegar", "conteudo",
        "arquivo", "leia", "exiba", "abra",
    ],
    "list_files": [
        "listar", "lista", "pasta", "diretorio", "dir", "arquivos",
        "pastas", "diretório", "ls",
    ],
    "screenshot": [
        "print", "captura", "tira", "foto", "tela", "screenshot",
        "capturar", "tirar", "imagem",
    ],
    "run_command": [
        "roda", "execute", "executa", "comando", "bash", "shell",
        "instala", "cria", "faz", "remove", "deleta", "apaga",
    ],
    "write_file": [
        "escreve", "salva", "cria arquivo", "cria um arquivo",
    ],
    "open_url": [
        "abre", "abrir", "navegador", "browser", "site", "url",
        "youtube", "google", "link", "pagina", "página",
    ],
    "listen": [
        "escuta", "ouve", "ouvir", "tocando", "musica", "música",
        "som", "áudio", "audio", "chamada", "call",
    ],
}
