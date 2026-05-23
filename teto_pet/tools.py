import os
import io
import base64
import subprocess
import tempfile

from PIL import ImageGrab

MAX_FILE_CHARS = 2000


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
}
