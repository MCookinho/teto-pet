import os
import io
import base64

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
    except Exception as e:
        return f"Erro ao ler {path}: {e}"


def list_files(path="."):
    expanded = os.path.expanduser(path)
    if not os.path.exists(expanded):
        return f"Erro: pasta não encontrada: {path}"
    try:
        items = []
        for item in sorted(os.listdir(expanded)):
            full = os.path.join(expanded, item)
            suffix = "/" if os.path.isdir(full) else ""
            items.append(f"{item}{suffix}")
        return "\n".join(items)
    except Exception as e:
        return f"Erro ao listar {path}: {e}"


def screenshot():
    try:
        img = ImageGrab.grab()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"Erro ao capturar tela: {e}"


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

TOOL_DESCRIPTION = """\
Você tem acesso a estas ferramentas:
- read_file(path): lê um arquivo de texto
- list_files(path): lista arquivos de uma pasta
- screenshot(): tira um print da tela

Para usar, responda EXATAMENTE neste formato:
{"tool": "nome_da_ferramenta", "args": {"param": "valor"}}
Depois receberá o resultado e poderá continuar a conversa.
Se não precisar de ferramenta, responda normalmente.
"""
