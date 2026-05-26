"""
Chat interface window for the desktop pet companion.

Provides a full conversation UI with:
- Chat bubble display with message history persistence
- Text entry and send functionality
- Tool execution based on natural language commands (open URLs, screenshot,
  file operations, system info queries, desktop audio listening)
- Speech-to-text via microphone button (STT with Groq API integration)
- AI provider integration for conversational replies and tool-mediated
  responses
- Automatic mood detection from user and assistant message content
"""

import os
import json
import html
import re
import threading
import subprocess

from gi.repository import Gtk, Pango, GObject, GLib

from desktop_pet import ai, config
from desktop_pet.log import log
from desktop_pet.character import Mood
from desktop_pet.models import model
from desktop_pet.tools import TOOLS, screenshot as _screenshot_fn, listen as _listen_fn, listen_mic

HISTORY_DIR = os.path.expanduser("~/.config/teto-pet/history")
MAX_HISTORY = 50


# ── History Management ──


def _history_path():
    """Return the filesystem path for the current model's history JSON file."""
    return os.path.join(HISTORY_DIR, f"{model.MODEL_ID}.json")


def _save_history(history):
    """Persist the conversation history to disk, keeping only the last MAX_HISTORY entries."""
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(_history_path(), "w", encoding="utf-8") as f:
            json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False)
    except Exception as e:
        log("erro salvando histórico: %s", e)


def _load_history():
    """Load conversation history from disk, returning an empty list on failure."""
    try:
        with open(_history_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ── Mood Detection ──


def _detect_mood(text):
    """
    Infer character mood from message content using keyword and pattern matching.

    Checks for explicit insults (complex multi-clause regex), then falls back
    on keyword sets for triste/raiva/feliz. Returns Mood.NORMAL when no
    sentiment is detected.
    """
    lower = text.lower()
    # Multi-pattern regex matching insults or dismissal commands:
    #   "te odeio/detesto/... de ...",
    #   "teto é ...",
    #   "você é (muito) (chata|ruim|horrivel|...)",
    #   "(que) chata que você é",
    #   "cala a boca / some daqui / desliga / fecha essa janela"
    if re.search(
        r'(?:te\s+(?:odeio|odio|detesto|acho|considero|chamo)\s+de\s+'
        r'|teto\s+(?:é|eh)\s+'
        r'|você\s+(?:é|eh)\s+(?:muito\s+)?(?:chata|ruim|horrível|horrivel|inútil|inutil|idiota|feia|boba|burra|nojenta|chatona)'
        r'|(?:que\s+)?chata\s+(?:que\s+)?você\s+é'
        r'|cala\s+a\s+boca|some\s+daqui|desliga|fecha\s+(?:essa\s+)?janela)',
        lower,
    ):
        return Mood.TRISTE
    words = set(lower.split())
    if words & {"triste", "chateado", "chateada", "depre", "mal", "tristeza", "sorry", "desculpa"}:
        return Mood.TRISTE
    if words & {"raiva", "ódio", "odio", "puto", "puta", "raiva", "bravo", "brava"}:
        return Mood.RAIVA
    if words & {"feliz", "alegre", "haha", "kkk", "amo", "adoro", "top", "ótimo", "otimo", "legal", "bom"}:
        return Mood.FELIZ
    return Mood.NORMAL


# ── URL Utilities ──


# Matches http://, https://, or bare www. URLs, excluding angle brackets
# and quotes that often delimit non-URL text.
_URL_RE = re.compile(r'(https?://[^\s<>"]+|www\.[^\s<>"]+)', re.I)


def _linkify(text):
    """
    Convert URLs in plain text into clickable HTML anchor tags.

    Splits text at each URL match, escapes plain segments with html.escape(),
    and wraps matched URLs in <a href="...">...</a> tags.
    """
    parts = []
    last = 0
    for m in _URL_RE.finditer(text):
        start, end = m.start(), m.end()
        if start > last:
            parts.append(html.escape(text[last:start]))
        url = m.group(0)
        href = url if url.startswith("http") else f"https://{url}"
        parts.append(f'<a href="{html.escape(href)}">{html.escape(url)}</a>')
        last = end
    if last < len(text):
        parts.append(html.escape(text[last:]))
    return "".join(parts)


def _open_url(url):
    """Open a URL in the system's default browser via xdg-open."""
    try:
        subprocess.run(["xdg-open", url], capture_output=True, timeout=5)
    except Exception:
        pass


# ── Tool Display Helpers ──


def _tool_display_words(result):
    """Map a tool execution result prefix to a friendly display phrase."""
    if result.startswith("run_command"):
        return model.phrases.pick("CMD_SUCCESS", "Feito! ^_^")
    if result.startswith("open_url"):
        return "Abrindo! ^_^"
    if result.startswith("screenshot"):
        return model.phrases.pick("SCREENSHOT_TAKEN", "Deixa eu ver... ^_^")
    if result.startswith("listen_erro"):
        return model.phrases.pick("LISTENING", "Escutando! ^_^")
    if result.startswith("listen"):
        return model.phrases.pick("LISTENING", "Escutando! ^_^")
    if result.startswith("write_file"):
        return model.phrases.pick("FILE_SAVED", "Salvo! ^_^")
    if result.startswith("list_files"):
        return "Pronto! ^_^"
    if result.startswith("read_file"):
        return "Entendi! ^_^"
    return "Feito! ^_^"


class ChatWindow(Gtk.Window):
    """
    Main chat dialog window.

    Emits two custom signals:
    - teto-speech:  (str, object) → text and Mood for the pet to speak
    - alarm-command: (str,)       → raw user text containing alarm/stop words
    """

    __gsignals__ = {
        "teto-speech": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
        "alarm-command": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    # ── Initialization ──

    def __init__(self, parent=None):
        """Build the chat window layout: message list, entry box, send + mic buttons."""
        super().__init__(title=f"Conversar com {model.PET_SHORT_NAME}", transient_for=parent)
        self.set_default_size(360, 420)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(sw, True, True, 0)

        self.msg_list = Gtk.ListBox()
        self.msg_list.set_selection_mode(Gtk.SelectionMode.NONE)
        sw.add(self.msg_list)

        entry_box = Gtk.Box(spacing=6)
        entry_box.set_margin_start(8)
        entry_box.set_margin_end(8)
        entry_box.set_margin_top(8)
        entry_box.set_margin_bottom(8)
        vbox.pack_start(entry_box, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Digite sua mensagem...")
        self.entry.connect("activate", self._on_send)
        entry_box.pack_start(self.entry, True, True, 0)

        send_btn = Gtk.Button.new_from_icon_name(
            "mail-send", Gtk.IconSize.BUTTON
        )
        send_btn.connect("clicked", self._on_send)
        entry_box.pack_start(send_btn, False, False, 0)

        self.mic_btn = Gtk.Button.new_from_icon_name(
            "audio-input-microphone", Gtk.IconSize.BUTTON
        )
        self.mic_btn.set_tooltip_text("Falar (STT)")
        self.mic_btn.connect("button-press-event", self._on_mic_press)
        self.mic_btn.connect("button-release-event", self._on_mic_release)
        entry_box.pack_start(self.mic_btn, False, False, 0)

        self.history = _load_history()
        self.waiting = False

        if not self.history:
            self._add_bubble(model.PET_SHORT_NAME, model.phrases.pick("GREETING", "Oii! Que bom te ver! ^_^"), "teto")
        else:
            for h in self.history[-20:]:
                who = model.PET_SHORT_NAME if h["role"] == "assistant" else "Você"
                self._add_bubble(who, h["content"], "teto" if h["role"] == "assistant" else "user")

    # ── Bubble Rendering ──

    def _add_bubble(self, who, text, cls):
        """
        Append a chat bubble to the message list.

        Parameters:
            who  – display name (e.g. "Você" or pet name)
            text – message body (auto-linkified)
            cls  – CSS-like class: "user" right-aligns, "teto" left-aligns
        """
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(spacing=4)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        label = Gtk.Label()
        who_escaped = html.escape(who)
        text_markup = _linkify(text)
        label.set_markup(f"<b>{who_escaped}:</b>  {text_markup}")
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_max_width_chars(38)
        label.set_xalign(0.0)
        label.connect("activate-link", lambda _l, uri: (_open_url(uri), True)[1])

        if cls == "user":
            hbox.pack_end(label, False, False, 0)
        else:
            hbox.pack_start(label, False, False, 0)

        row.add(hbox)
        self.msg_list.add(row)
        self.msg_list.show_all()

        # Auto-scroll to bottom
        adj = self.msg_list.get_parent().get_vadjustment()
        if adj:
            adj.set_value(adj.get_upper() - adj.get_page_size())

        return row

    # ── Tool Execution ──

    # Common verb/directory patterns reused across multiple tool-matching branches.
    _LIST_VERBS = r'(?:listar?|lista|mostra|mostre|exibir?|veja?|olha?)'
    _DIR_KEYWORDS = r'(?:pastas?|home|diretorio|dir|area)'
    _READ_VERBS = r'(?:ler|abrir|abra?|leia?|exibe?|pegar?|conteudo|mostra)'

    def _run_tool(self, text):
        """
        Parse user text and attempt to match a known tool command.

        Checks are ordered by specificity/priority:
          1. open_url   – direct URLs, named channels, known sites, generic "abre ..."
          2. screenshot – screen capture keywords
          3. listen     – desktop audio capture keywords
          4. list_files – directory listing patterns
          5. read_file  – file content reading patterns
          6. write_file – file creation/save patterns
          7. run_command – shell command / install patterns
          8. system info – hardware/OS queries (only if tools are permitted)
          9. app launch  – application name matching (only if tools are permitted)

        Returns a result string on match, or None to fall through to AI.
        """
        lower = text.lower().strip()
        cfg = config.load()
        permitted = any(cfg.get(k, False) for k in config.TOOL_KEYS)

        # ── open_url (before read_file to avoid 'abra' clash) ──
        if permitted:
            # 1) Explicit URLs – detect raw http(s) links
            m = re.search(r'(https?://\S+)', text)
            if m:
                return self._exec("open_url", {"url": m.group(1)})

            # 2) "abre/abra/abrir o canal do X [no youtube]" – search YouTube channel
            m = re.search(
                r'(?:abre|abra|abrir)\s+o\s+canal\s+(?:do|da)\s+(.+?)(?:\s*no\s+youtube)?\s*$',
                text, re.I,
            )
            if m:
                q = m.group(1).strip().rstrip(".,!?")
                # Strip trailing filler words like "entao", "pf", "la", etc.
                q = re.sub(r'\s+(?:entao|então|pf|por\s+favor|la|lá|ai|aí)\s*$', '', q, flags=re.I)
                if q:
                    return self._exec("open_url", {"url": f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}"})

            # 3) "canal do X [no youtube]" / "youtuber X" – shortcut for channel search
            m = re.search(
                r'(?:canal\s+(?:do|da)\s+|youtube\s+(?:do|da)\s+|youtuber\s+)'
                r'(.+?)(?:\s*no\s+youtube)?\s*$',
                text, re.I,
            )
            if m:
                q = m.group(1).strip().rstrip(".,!?")
                return self._exec("open_url", {"url": f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}"})

            # 4) "quero/queria assistir/ver X [no youtube]" – expressed desire to watch
            m = re.search(
                r'quero\s+(?:assistir|ver)\s+(?:o\s+|a\s+)?(.+?)(?:\s*no\s+youtube)?\s*$',
                text, re.I,
            )
            if m:
                q = m.group(1).strip().rstrip(".,!?")
                return self._exec("open_url", {"url": f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}"})

            # 5) "abre/abra NOME conhecido (youtube, google, github, etc)" → open known site URL
            known_sites = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "github": "https://github.com",
                "gmail": "https://mail.google.com",
                "maps": "https://maps.google.com",
                "reddit": "https://www.reddit.com",
                "twitter": "https://x.com",
                "instagram": "https://www.instagram.com",
                "facebook": "https://www.facebook.com",
                "whatsapp": "https://web.whatsapp.com",
                "amazon": "https://www.amazon.com",
                "netflix": "https://www.netflix.com",
                "spotify": "https://open.spotify.com",
                "linkedin": "https://www.linkedin.com",
                "chatgpt": "https://chatgpt.com",
                "deepseek": "https://chat.deepseek.com",
            }
            site_keys = '|'.join(known_sites.keys())
            # Match "abre youtube", "abra o github", "quero abrir google", etc.
            site_pattern = r'(?:abre|abra|abrir|pode\s+abrir|queria\s+abrir|quero\s+abrir|abre\s+ai|abre\s+lá)\s+' \
                          r'(?:(?:a|o|esse|esta|meu|minha)\s+)?(' + site_keys + r')'
            m = re.search(site_pattern, text, re.I)
            if m:
                site_key = m.group(1).lower().strip()
                url = known_sites.get(site_key, f"https://www.{site_key}.com")
                return self._exec("open_url", {"url": url})

            # 6) "abre/abra NOME" (no "canal") → generic URL or Google search fallback
            if re.search(r'\b(?:site|pagina|link)\b', lower):
                m = re.search(r'(?:abre|abra|abrir|acessa|acessar)\s+(?:o\s+|a\s+)?(.+)', text, re.I)
                if m:
                    q = m.group(1).strip().rstrip(".,!?")
                    # If it looks like a domain (has TLD), prepend https://; otherwise search
                    if not re.match(r'https?://', q):
                        q = f"https://{q}" if re.search(r'\.[a-z]{2,}', q) else f"https://www.google.com/search?q={q.replace(' ', '+')}"
                    return self._exec("open_url", {"url": q})

        # ── screenshot ────────────────────────────────────
        # Match various Portuguese phrases for taking a screenshot
        if re.search(
            r'(?:\bprint\b|captura\s*de\s*tela|tira\s+foto|foto\s+da\s+tela|'
            r'\bscreenshot\b|mostra\s+a\s+tela|olha\s+a\s+tela|'
            r'veja?\s+o\s+que\s+tem\s+na\s+tela|'
            r'(?:oq|o\s+que|oque)\s+tem\s+na\s+(?:minha\s+)?tela)',
            lower,
        ):
            return self._exec("screenshot", {})

        # ── listen ─────────────────────────────────────────
        # Match requests to listen to desktop audio / identify playing music
        if re.search(
            r'(?:escuta|ouve|ouvir|o\s+que\s+[eé]\s+que\s+ta\s+tocando|'
            r'que\s+musica|que\s+música|'
            r'escuta\s+o\s+que\s+[eé]\s+que\s+ta\s+tocando|'
            r'escuta\s+o\s+que\s+ta\s+rolando|'
            r'o\s+que\s+ta\s+tocando|'
            r'escuta\s+o\s+som|escuta\s+o\s+audio|escuta\s+o\s+áudio|'
            r'ta\s+tocando\s+o\s+que)',
            lower,
        ):
            return self._exec("listen", {})

        # ── list files ────────────────────────────────────
        # "o que tem [em/na/no/nas/nos] X" – but NOT when talking about arquivo/documento
        if re.search(r'(?:o\s+)?(?:que|q)\s+tem\s+(?:e[mn]|na[rs]?|no[rs]?)\s+', lower) \
                and not re.search(r'(?:arquivo|documento|texto|conteudo)\s', lower):
            m = re.search(r'(?:o\s+)?(?:que|q)\s+tem\s+(?:e[mn]|na[rs]?|no[rs]?)\s+(.+)', lower, re.I)
            if m:
                return self._exec("list_files", {"path": self._parse_path(m.group(1))})

        # "veja/lista/mostra [a/o/as] pasta/home/diretorio"
        if re.search(rf'{self._LIST_VERBS}\s+', lower) \
                and re.search(self._DIR_KEYWORDS, lower) \
                and not re.search(r'(?:arquivo|documento|texto|conteudo)', lower):
            m = re.search(rf'(?:{self._DIR_KEYWORDS})\s*(.+)?$', lower, re.I)
            raw = m.group(1).strip() if m and m.group(1) else "~"
            return self._exec("list_files", {"path": self._parse_path(raw)})

        # "minha pasta", "meu home", "pasta home"
        if re.search(r'(?:minha\s+pastas?|meu\s+home|pastas?\s+home)', lower) \
                and not re.search(r'(?:arquivo|documento|texto)', lower):
            return self._exec("list_files", {"path": "~"})

        # "lista/veja [em/na] X" – simple path listing
        m = re.search(
            rf'^{self._LIST_VERBS}\s+(?:pra\s+mim\s+)?(?:o\s+)?(?:que\s+)?(?:tem\s+)?'
            rf'(?:em|na|no|nesse|nessa)\s+["\']?(.+?)["\']?$',
            text, re.I,
        )
        if m:
            raw = m.group(1).strip()
            if raw and not re.search(r'(?:arquivo|documento|conteudo)', raw):
                return self._exec("list_files", {"path": self._parse_path(raw)})

        # "lista X" – single word path argument
        m = re.search(r'^(?:listar?|lista)\s+["\']?(\S+)["\']?$', text.strip(), re.I)
        if m:
            return self._exec("list_files", {"path": self._parse_path(m.group(1))})

        # "leia/abra a pasta/home/diretorio" → redirect to list_files
        if re.search(r'(?:ler|abra?|leia?|abrir)\s+(?:a\s+|o\s+)?(?:pastas?|home|diretorio)', lower):
            m = re.search(r'(?:ler|abra?|leia?|abrir)\s+(?:a\s+|o\s+)?(?:pastas?|home|diretorio)\s+(.+)?$', lower)
            path = m.group(1).strip() if m and m.group(1) else "~"
            return self._exec("list_files", {"path": self._parse_path(path)})

        # ── read file ─────────────────────────────────────
        if re.search(self._READ_VERBS, lower) \
                and re.search(r'(?:arquivo|documento|texto|conteudo|\.\w{1,5}\s*$)', lower):
            # Match quoted filename: "leia 'arquivo.txt'" or "abra o arquivo chamado 'foo'"
            m = re.search(
                rf'{self._READ_VERBS}\s+(?:o\s+)?(?:arquivo\s+)?(?:chamado\s+)?'
                rf'["\'](.+?)["\']',
                text, re.I,
            )
            if m:
                return self._exec("read_file", {"path": self._parse_path(m.group(1).strip())})
            # Fallback: match unquoted single-word filename
            m = re.search(
                rf'{self._READ_VERBS}\s+(?:o\s+)?(?:arquivo\s+)?(?:chamado\s+)?'
                rf'(\S+)',
                text, re.I,
            )
            if m:
                path = m.group(1).strip()
                if not re.search(r'^(?:pastas?|home|diretorio|meu|minha|na|no|em|a\s+|o\s+)', path, re.I):
                    return self._exec("read_file", {"path": self._parse_path(path)})

        # ── write file ────────────────────────────────────
        # "cria/salva/escreve [um] arquivo X [com] Y" — quoted filename + content
        m = re.search(
            r'(?:cria|salva|escreve|criar)\s+(?:um\s+)?arquivo\s+["\']?(.+?)["\']?\s+'
            r'(?:com\s+(?:o\s+)?(?:conteudo|texto)?\s*)(.+)',
            text, re.I | re.DOTALL,
        )
        if m:
            return self._exec("write_file", {
                "path": m.group(1).strip(),
                "content": m.group(2).strip(),
            })

        # "escreve EM/NO/NA X: Y" — path after preposition, content after colon
        m = re.search(
            r'(?:escreve|salva)\s+(?:em|no|na)\s+["\']?(.+?)["\']?\s*:\s*(.+)',
            text, re.I | re.DOTALL,
        )
        if m:
            return self._exec("write_file", {
                "path": m.group(1).strip(),
                "content": m.group(2).strip(),
            })

        # ── run command ───────────────────────────────────
        # "roda/execute/executa X"
        m = re.search(r'(?:roda|execute|executa|rodar|vamos\s+lá)\s+(.*)', text, re.I)
        if m:
            return self._exec("run_command", {"command": m.group(1).strip()})

        # "instala X"
        m = re.search(r'(?:instala|instalar)\s+(.*)', text, re.I)
        if m:
            return self._exec("run_command", {"command": m.group(1).strip()})

        # ── system info queries (only with assistente_local) ──
        if permitted:
            if re.search(r'(?:sistema\s+operacional|qual\s+(?:o\s+)?(?:sistema|SO|os)|que\s+(?:SO|os)\s+(?:eu\s+)?(?:tenho|uso)|qual\s+distro)', lower):
                return self._exec("run_command", {"command": "cat /etc/os-release 2>/dev/null | head -5 || lsb_release -d 2>/dev/null || uname -o"})
            if re.search(r'(?:mem[óo]ria|RAM|quanta\s+ram|memoria\s+ram|mem[óo]ria\s+total)', lower):
                return self._exec("run_command", {"command": "free -h | head -3"})
            if re.search(r'(?:processador|CPU|qual\s+(?:o\s+)?processador|quantos\s+n[uú]cleos)', lower):
                return self._exec("run_command", {"command": "lscpu | grep -E '^(Model name|CPU|Thread|Core|Socket)' | head -5"})
            if re.search(r'(?:disco|hd|armazenamento|espa[çc]o\s+(?:em\s+)?disco|quanto\s+espa[çc]o)', lower):
                return self._exec("run_command", {"command": "df -h / 2>/dev/null | tail -1"})
            if re.search(r'(?:kernel|vers[ãa]o\s+do\s+linux|uname)', lower):
                return self._exec("run_command", {"command": "uname -a"})
            if re.search(r'(?:hostname|nome\s+(?:do\s+)?(?:pc|computador|maquina))', lower):
                return self._exec("run_command", {"command": "hostname"})
            if re.search(r'(?:usu[áa]rio|usuario|quem\s+(?:sou|é|est[áa]))\s+(?:eu|logado|no\s+pc)', lower):
                return self._exec("run_command", {"command": "whoami"})
            if re.search(r'(?:tempo\s+(?:ligado|online|ativo)|uptime|h[aá] quanto\s+tempo)', lower):
                return self._exec("run_command", {"command": "uptime"})
            if re.search(r'(?:processos?|programas?\s+(?:abertos|rodando|executando)|o\s+que\s+est[áa]\s+rodando)', lower):
                return self._exec("run_command", {"command": "ps aux --sort=-%mem | head -10"})
            if re.search(r'(?:rede|IP|endere[çc]o\s+(?:de\s+)?(?:rede|ip)|conex[ãa]o|wifi)', lower):
                return self._exec("run_command", {"command": "ip -4 a 2>/dev/null || ifconfig 2>/dev/null | head -10"})
            if re.search(r'(?:nomes?[ãa]o|data|que\s+(?:dia|hora)\s+(?:é|são|estamos)|hor[aá]rio)', lower):
                return self._exec("run_command", {"command": "date '+%A, %d de %B de %Y - %H:%M'"})
            if re.search(r'(?:placa\s+(?:de\s+)?(?:v[íi]deo|gr[áa]fica)|GPU|qual\s+(?:a\s+)?placa)', lower):
                return self._exec("run_command", {"command": "lspci | grep -i vga | head -3"})
            if re.search(r'(?:bateria|nível\s+da\s+bateria|carga|energy)', lower):
                return self._exec("run_command", {"command": "cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1 || echo 'Sem bateria detectada'"})

        # ── app launch ────────────────────────────────────
        if permitted:
            # "abre/abra/inicia/roda X" — capture the app name from a variety of verb prefixes,
            # stripping leading determiners / filler words before it.
            m = re.search(
                r'(?:abre|abra|abrir|inicia|iniciar|roda|rodar|'
                r'pode\s+abrir|poderia\s+abrir|queria\s+abrir|quero\s+abrir)\s+'
                r'(?:(?:a|o|as|os|esse|esta|este|esses|essas|essa|isso|'
                r'meu|minha|meus|minhas|teu|tua|seu|sua|'
                r'pra|pro|para|mim|pf|la|lá|ai|aí|por\s+favor)\s+)*'
                r'(\w[\w.\-]*)',
                text, re.I,
            )
            if m:
                app = m.group(1).strip().rstrip(".,!?")
                # Guard against accidentally matching channel/site/URL patterns
                if not re.search(r'(canal|site|youtube|https?://|\.[a-z]{2,})', lower) \
                        and app.lower() not in ("app", "site", "link", "pagina", "página", "isso", "isto", "aquilo", "coisa", "programa", "aplicativo", "meu", "minha", "meus", "minhas", "teu", "tua", "seu", "sua"):
                    return self._exec("run_command", {"command": f"({app} &)"})

        # ── fallback: try as command ──
        if permitted:
            # Direct match for common CLI tools (git, mkdir, apt, pip, etc.)
            if re.search(r'^(?:git|mkdir|touch|cp|mv|rm|apt|pip|npm|yarn|docker|make|cmake|sudo)\s', text.strip()):
                return self._exec("run_command", {"command": text.strip()})

        return None

    # ── Path Resolution ──

    def _parse_path(self, raw):
        """
        Normalise a user-supplied path string to an absolute filesystem path.

        Strips filler words and directory keywords, expands ``~``, and falls
        back to case-insensitive matching via _resolve_ci.  Returns ``"~"``
        when no specific path is identifiable.
        """
        raw = raw.strip().rstrip(".,!?;:")
        # Strip leading filler words and directory keywords:
        #   "minha pasta home", "meu diretorio", "a pasta", etc.
        raw = re.sub(
            r'^(?:(?:minha|meu|nossa|nosso|suas?|tuas?|a|o|as|os|da|do|das|dos|de|em|no|na|nos|nas|'
            r'pastas?|diretorio|dir|home|pasta)\s+)+',
            '', raw, re.I,
        )
        if not raw or re.search(r'^(?:(?:minha\s+)?(?:home|pastas?(?:\s+home)?|diretorio)|meu\s+home)\s*$', raw, re.I):
            return "~"
        expanded = os.path.expanduser(raw)
        if os.path.exists(expanded):
            return expanded
        resolved = _resolve_ci(expanded)
        if resolved:
            return resolved
        if not raw.startswith("~") and not raw.startswith("/") and not raw.startswith("."):
            expanded = os.path.expanduser(f"~/{raw}")
            if os.path.exists(expanded):
                return expanded
            resolved = _resolve_ci(expanded)
            if resolved:
                return resolved
        return raw

    # ── Tool Executor ──

    def _exec(self, tool_name, args):
        """
        Execute a named tool by looking it up in the TOOLS registry.

        Checks the config permission flag for the tool, resolves any ``path``
        argument case-insensitively, invokes the tool's ``execute`` callback,
        and formats the result with a tool-specific prefix for downstream
        processing.
        """
        cfg = config.load()
        tool_cfg_key = f"tool_{tool_name}"
        if not cfg.get(tool_cfg_key, False):
            return None

        tool = TOOLS.get(tool_name)
        if not tool:
            return None

        # resolve paths case-insensitively
        if "path" in args:
            args["path"] = self._parse_path(args["path"])

        try:
            result = tool["execute"](**args)
        except TypeError as e:
            return f"erro: argumentos inválidos pra {tool_name}: {e}"
        if tool_name == "screenshot":
            return f"screenshot:{result}"
        if tool_name == "listen":
            if result.startswith("Erro:") or result.startswith("Não"):
                return f"listen_erro:{result}"
            return f"listen:{result}"
        if tool_name == "run_command":
            log("Comando: %s", args.get('command', '?')[:60])
        if 'path' in args:
            log("Arquivo: %s", args.get('path', '?'))
        log("%s → %s", tool_name, result[:60])
        display_arg = args.get('path') or args.get('url') or '~'
        return f"{tool_name}({display_arg}): {result[:1000]}"

    # Matches "TOOL: toolname | key=val | key=val" patterns in AI replies.
    _TOOL_RE = re.compile(r'TOOL\s*:\s*(\w+)(?:\s*\|\s*(.+))?', re.I)

    # ── History Management ──

    def clear_history(self):
        """Reset conversation history and re-show the greeting message."""
        self.history = []
        for row in list(self.msg_list.get_children()):
            self.msg_list.remove(row)
        self._add_bubble(model.PET_SHORT_NAME, model.phrases.pick("GREETING", "Oii! Que bom te ver! ^_^"), "teto")
        try:
            os.remove(_history_path())
        except OSError:
            pass

    def add_message(self, text):
        """Append an assistant message bubble and persist to history."""
        self._add_bubble(model.PET_SHORT_NAME, text, "teto")
        self.history.append({"role": "assistant", "content": text})
        _save_history(self.history)

    # ── AI Callback ──

    def _call_ai_then_tool(self, text, depth=0, image_base64=None, silent=False):
        """
        Send user text to the AI provider and process the reply.

        The AI reply is inspected for a ``TOOL:`` directive.  When found the
        named tool is executed and the result is fed back into the AI (up to
        ``depth`` 3 to avoid infinite loops).  When no tool is requested the
        reply is displayed as a chat bubble and emitted as speech.

        Parameters:
            text         – the user / context message
            depth        – recursion counter for tool call chaining
            image_base64 – optional base64-encoded image for vision models
            silent       – if True, suppresses the thinking bubble and entry lock
        """
        if depth > 3:
            return model.phrases.pick("TOOL_LOOP", "Hmm, deu um loop nas ferramentas! >_<")

        if not silent:
            self.waiting = True
            self.entry.set_sensitive(False)
            # Safety timeout: re-enable entry after 30 seconds if no reply arrives
            GLib.timeout_add_seconds(15, self._unlock_entry)
        thinking_row = self._add_bubble(model.PET_SHORT_NAME, "…", "teto") if not silent else None
        user_mood = _detect_mood(text)

        def on_reply(reply):
            if thinking_row:
                self.msg_list.remove(thinking_row)

            self._safe_entry()

            if silent and not reply:
                return

            # Check for a TOOL directive in the AI's response
            m = self._TOOL_RE.search(reply) if reply else None
            if m:
                tool_name = m.group(1).lower()
                args_raw = m.group(2) or ""
                args = {}
                for pair in args_raw.split("|"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        v = v.strip()
                        # Strip trailing emotes/kaomoji from the value (e.g. >_<, ^_^, :3)
                        v = re.sub(r'\s*[>_<^:;)\]}\-]+\s*(?:[>_<^:;)\]}\-\d]+\s*)*$', '', v)
                        args[k.strip()] = v

                if tool_name == "screenshot":
                    img = _screenshot_fn()
                    if img and not img.startswith("erro") and not img.startswith("Não"):
                        self._call_ai_then_tool(
                            "Descreva o que você vê nesta captura de tela.",
                            depth + 1, image_base64=img, silent=True,
                        )
                        return
                    fail_msg = model.phrases.pick("SCREENSHOT_FAILED", "Não consegui capturar a tela...")
                    self._add_bubble(model.PET_SHORT_NAME, img or fail_msg, "teto")
                    self.emit("teto-speech", img or fail_msg, Mood.TRISTE)
                    return

                if tool_name == "listen":
                    audio_path = _listen_fn()
                    if audio_path and os.path.exists(audio_path):
                        transcribed = ai.transcribe(audio_path)
                        if transcribed:
                            self._call_ai_then_tool(
                                f"{text}\n\n[Áudio capturado do desktop]\n"
                                f"Transcrição: {transcribed}\n\n"
                                f"Comente naturalmente sobre o que ouviu na tela "
                                f"do usuário.",
                                depth + 1, silent=True,
                            )
                        else:
                            self._call_ai_then_tool(
                                f"{text}\n\n[Não entendi o áudio do desktop]\n\n"
                                f"Comente que não deu pra entender o som.",
                                depth + 1, silent=True,
                            )
                    else:
                        fail_msg = model.phrases.pick("AUDIO_FAILED", "Não consegui capturar o áudio...")
                        self._add_bubble(model.PET_SHORT_NAME, audio_path or fail_msg, "teto")
                        self.emit("teto-speech", audio_path or fail_msg, Mood.TRISTE)
                    return

                tool_result = self._exec(tool_name, args)
                if tool_result:
                    self.history.append({"role": "assistant", "content": f"[Ferramenta {tool_name} executada]"})
                    self._call_ai_then_tool(
                        f"{text}\n\n[Resultado de {tool_name}: {tool_result}]",
                        depth + 1, silent=True,
                    )
                else:
                    bubble_text = model.phrases.pick("TOOL_FAILED", "Hmm, não consegui usar essa ferramenta...")
                    self.history.append({"role": "assistant", "content": bubble_text})
                    _save_history(self.history)
                    self._add_bubble(model.PET_SHORT_NAME, bubble_text, "teto")
                    self.emit("teto-speech", bubble_text, Mood.TRISTE)
                return

            if reply:
                self.history.append({"role": "assistant", "content": reply})
                _save_history(self.history)

                reply_mood = _detect_mood(reply)
                if reply_mood == Mood.NORMAL and user_mood != Mood.NORMAL:
                    reply_mood = user_mood

                self._add_bubble(model.PET_SHORT_NAME, reply, "teto")
                self.emit("teto-speech", reply, reply_mood)

        if image_base64:
            ai.ask(text, self.history, callback=on_reply, image_base64=image_base64)
        else:
            ai.ask(text, self.history, callback=on_reply)

    # ── Microphone STT ──

    def _on_mic_press(self, btn, event):
        """
        Start microphone recording on button press.

        Records in a background thread for ``hold`` (30 s, released on button
        release) or ``toggle`` (5 s, auto-stop) mode.  On successful capture
        the audio is transcribed via ``ai.transcribe()`` and the result is
        submitted as a chat message.
        """
        cfg = config.load()
        if not cfg.get("mic_stt_enabled", False):
            self._add_bubble(model.PET_SHORT_NAME, "STT por microfone está desativado. Ative em Configurações > Áudio.", "teto")
            return True
        if not cfg.get("groq_key", ""):
            self._add_bubble(model.PET_SHORT_NAME, "Configure a chave do Groq em Configurações > Inteligência > Configurar Groq... para usar STT.", "teto")
            return True

        mode = cfg.get("mic_stt_mode", "toggle")
        self._stt_stop_event = threading.Event()
        device = cfg.get("mic_stt_device", "") or None

        if mode == "hold":
            duration = 30
            self.mic_btn.set_tooltip_text("Gravando... solte para parar")
            self.entry.set_placeholder_text("Gravando... (solte para parar)")
        else:
            duration = 5
            self.mic_btn.set_tooltip_text("Gravando...")
            self.entry.set_placeholder_text("Gravando...")

        def record():
            log("STT: gravando do dispositivo %s", device or "(auto)")
            wav = listen_mic(device=device, duration=duration, stop_event=self._stt_stop_event)
            if isinstance(wav, str) and wav.startswith("Erro"):
                log("STT: erro na captura: %s", wav)
                GLib.idle_add(self._add_bubble, model.PET_SHORT_NAME, wav, "teto")
            elif wav:
                log("STT: áudio capturado, transcrevendo...")
                text = ai.transcribe(wav)
                # Only accept transcription that contains at least one alphabetic character
                if text and re.search(r'[a-zA-Záéíóúâêîôûãõçàèìòùäëïöüñ]', text):
                    log("STT: transcrição: %s", text)
                    GLib.idle_add(self.entry.set_text, text)
                    GLib.idle_add(self._on_send)
                else:
                    log("STT: transcrição falhou%s", f" ({text})" if text else "")
                    GLib.idle_add(self._add_bubble, model.PET_SHORT_NAME,
                                  "Não entendi o que você falou... Tenta de novo!", "teto")
            GLib.idle_add(self.mic_btn.set_tooltip_text, "Falar (STT)")
            GLib.idle_add(self.entry.set_placeholder_text, "Digite sua mensagem...")

        threading.Thread(target=record, daemon=True).start()
        return True

    def _on_mic_release(self, btn, event):
        """Stop microphone recording on button release (hold mode only)."""
        cfg = config.load()
        if cfg.get("mic_stt_mode", "") == "hold":
            log("STT: botão solto, parando gravação")
            if hasattr(self, '_stt_stop_event'):
                self._stt_stop_event.set()
        return True

    # ── Entry State ──

    def _safe_entry(self):
        """Re-enable the text entry and clear the waiting flag."""
        self.waiting = False
        self.entry.set_sensitive(True)

    def _unlock_entry(self):
        """
        Safety timeout callback: unlock the entry if still waiting.

        Fires after 15 seconds (two intervals via GLib.timeout_add_seconds)
        to prevent permanent UI lock when an AI reply never arrives.
        """
        if self.waiting:
            self._safe_entry()
            log("⚠ entrada destravada por segurança (30s)")
        return False

    # ── Message Processing ──

    def _process_user_text(self, text):
        """
        Handle an incoming user message end-to-end.

        Steps:
          1. Add a user bubble and append to history.
          2. Check for alarm/stop words and emit ``alarm-command`` if found.
          3. Attempt keyword-based tool matching via ``_run_tool``.
          4. On tool match: display feedback, optionally call AI with result.
          5. On no tool match: send to AI for a conversational reply.
        """
        text = text.strip()
        if not text or self.waiting:
            return
        self._add_bubble("Você", text, "user")
        self.history.append({"role": "user", "content": text})
        log("Você: %s", text)

        alarm_words = {"para", "pare", "parar", "desliga", "desligar", "cala", "calar", "stop", "chega"}
        if any(w in text.lower() for w in alarm_words):
            self.emit("alarm-command", text)

        kw_result = self._run_tool(text)
        if kw_result:
            cfg = config.load()
            words = _tool_display_words(kw_result)
            is_data_tool = kw_result.startswith("list_files") or kw_result.startswith("read_file")
            using_phrases = cfg.get("ai_provider", config.PROVIDER_AUTO) == config.PROVIDER_PHRASES
            if using_phrases:
                self._add_bubble(model.PET_SHORT_NAME, words, "teto")
                self.history.append({"role": "assistant", "content": words})
                _save_history(self.history)
                if not is_data_tool:
                    self.emit("teto-speech", words, Mood.NORMAL)
            else:
                log("%s: %s", model.PET_SHORT_NAME, words)

            if cfg.get("ai_provider", config.PROVIDER_AUTO) != config.PROVIDER_PHRASES:
                if kw_result.startswith("screenshot:"):
                    img_b64 = kw_result[len("screenshot:"):]
                    self._call_ai_then_tool(
                        "Descreva o que você vê nesta captura de tela em português, "
                        "com detalhes! Fale sobre os aplicativos abertos, janelas, "
                        "icones e qualquer coisa interessante na tela.",
                        silent=True, image_base64=img_b64,
                    )
                elif kw_result.startswith("listen_erro:"):
                    self._call_ai_then_tool(
                        f"{text}\n\n[Erro ao capturar áudio: {kw_result[len('listen_erro:'):]}]",
                        silent=True,
                    )
                elif kw_result.startswith("listen:"):
                    audio_path = kw_result[len("listen:"):]
                    if audio_path and os.path.exists(audio_path):
                        transcribed = ai.transcribe(audio_path)
                        if transcribed:
                            self._call_ai_then_tool(
                                f"{text}\n\n[Áudio capturado do desktop]\n"
                                f"Transcrição: {transcribed}\n\n"
                                f"Comente naturalmente sobre o que ouviu na tela "
                                f"do usuário.",
                                silent=True,
                            )
                        else:
                            self._call_ai_then_tool(
                                f"{text}\n\n[Não entendi o áudio do desktop]\n\n"
                                f"Comente que não deu pra entender o som.",
                                silent=True,
                            )
                    else:
                        self._call_ai_then_tool(
                            f"{text}\n\n[Não consegui capturar áudio]\n\n"
                            f"Comente que não conseguiu capturar o som.",
                            silent=True,
                        )
                else:
                    self._call_ai_then_tool(
                        f"{text}\n\n[Resultado de ferramenta: {kw_result}]\n\n"
                        f"Responda naturalmente como amiga, comentando o resultado.",
                        silent=False,
                    )
            return

        self._call_ai_then_tool(text)

    def _on_send(self, _widget=None):
        """Read the entry text, clear it, and process the message."""
        text = self.entry.get_text().strip()
        if not text or self.waiting:
            return
        self.entry.set_text("")
        self._process_user_text(text)


# ── Helpers ──


def _resolve_ci(path):
    """
    Resolve a filesystem path with case-insensitive segment matching.

    Walks each path component and compares against directory entries with
    ``lower()``, allowing the pet to find files even when the user's casing
    does not match the actual filesystem.
    """
    if os.path.exists(path):
        return path
    parts = path.strip("/").split("/")
    current = "/" if path.startswith("/") else ""
    if path.startswith("~"):
        current = os.path.expanduser("~")
        parts = parts[1:]
    for part in parts:
        if not part:
            continue
        if not os.path.isdir(current) and not os.path.isfile(current):
            return None
        try:
            for name in os.listdir(current):
                if name.lower() == part.lower():
                    current = os.path.join(current, name)
                    break
            else:
                return None
        except PermissionError:
            return None
    return current
