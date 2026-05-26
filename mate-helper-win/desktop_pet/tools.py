import os
import re
import subprocess

from desktop_pet import platform
from desktop_pet.log import log

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
    r'\bformat\s+[a-z]:',
    r'\bdel\s+/[fqs]\s+',
]
DANGEROUS_RE = re.compile('|'.join(DANGEROUS_PATTERNS))


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
    return platform.screenshot()


def run_command(command):
    if DANGEROUS_RE.search(command):
        return "Comando bloqueado por segurança (parece destrutivo demais)"
    expanded = os.path.expanduser(command)
    try:
        result = platform.run_shell(expanded, timeout=CMD_TIMEOUT)
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
    try:
        platform.open_url(url)
        return f"URL aberta: {url}"
    except Exception as e:
        return f"Erro ao abrir URL: {e}"


def list_mic_sources():
    devices = platform.list_audio_devices()
    return [d["id"] for d in devices]


def listen_mic(device=None, duration=5, stop_event=None):
    result = platform.record_mic(device, duration, stop_event)
    if isinstance(result, str) and os.path.exists(result):
        return result
    log("tools: listen_mic: %s", result)
    return None


def listen(duration=8):
    result = platform.record_desktop_audio(duration)
    if isinstance(result, str) and os.path.exists(result):
        return result
    if isinstance(result, str):
        log("tools: listen: %s", result)
    return None


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
        "description": "Executa um comando no computador",
        "execute": run_command,
        "parameters": {"command": "comando para executar"},
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
        "cmd", "powershell",
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
