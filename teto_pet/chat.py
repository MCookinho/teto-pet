import os
import re
import sys
import json
import html

from gi.repository import Gtk, Pango, GObject

from teto_pet import ai, config
from teto_pet.character import Mood
from teto_pet.tools import TOOLS, TOOL_KEYWORDS

HISTORY_FILE = os.path.expanduser("~/.config/teto-pet/chat_history.json")
MAX_HISTORY = 50


def _save_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False)
    except OSError:
        pass


def _load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _detect_mood(text):
    lower = text.lower()
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


class ChatWindow(Gtk.Window):

    __gsignals__ = {
        "teto-speech": (GObject.SignalFlags.RUN_FIRST, None, (str, object)),
    }

    def __init__(self, parent=None):
        super().__init__(title="Conversar com Teto", transient_for=parent)
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

        self.history = _load_history()
        self.waiting = False

        if not self.history:
            self._add_bubble("Teto", "Oii! Que bom te ver! ^_^", "teto")
        else:
            for h in self.history[-20:]:
                who = "Teto" if h["role"] == "assistant" else "Você"
                self._add_bubble(who, h["content"], "teto" if h["role"] == "assistant" else "user")

    def _add_bubble(self, who, text, cls):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(spacing=4)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        label = Gtk.Label()
        label.set_markup(f"<b>{who}:</b>  {html.escape(text)}")
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_max_width_chars(38)
        label.set_xalign(0.0)

        if cls == "user":
            hbox.pack_end(label, False, False, 0)
        else:
            hbox.pack_start(label, False, False, 0)

        row.add(hbox)
        self.msg_list.add(row)
        self.msg_list.show_all()

        adj = self.msg_list.get_parent().get_vadjustment()
        if adj:
            adj.set_value(adj.get_upper() - adj.get_page_size())

        return row

    _LIST_VERBS = r'(?:listar?|lista|mostra|mostre|exibir?|veja?|olha?)'
    _DIR_KEYWORDS = r'(?:pastas?|home|diretorio|dir|area)'
    _READ_VERBS = r'(?:ler|abrir|abra?|leia?|exibe?|pegar?|conteudo|mostra)'

    def _run_tool(self, text):
        lower = text.lower().strip()
        cfg = config.load()
        permitted = cfg.get("assistente_local", False)

        # ── screenshot ────────────────────────────────────
        if re.search(
            r'(?:\bprint\b|captura\s*de\s*tela|tira\s+foto|foto\s+da\s+tela|'
            r'\bscreenshot\b|mostra\s+a\s+tela|olha\s+a\s+tela|'
            r'veja?\s+o\s+que\s+tem\s+na\s+tela)',
            lower,
        ):
            return self._exec("screenshot", {})

        # ── list files ────────────────────────────────────
        # "o que tem [em/na/no/nas/nos] X" (NOT arquivo)
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
            path = m.group(1).strip() if m and m.group(1) else "~"
            return self._exec("list_files", {"path": path})

        # "minha pasta", "meu home", "pasta home"
        if re.search(r'(?:minha\s+pastas?|meu\s+home|pastas?\s+home)', lower) \
                and not re.search(r'(?:arquivo|documento|texto)', lower):
            return self._exec("list_files", {"path": "~"})

        # "lista/veja [em/na] X" (simple path)
        m = re.search(
            rf'^{self._LIST_VERBS}\s+(?:pra\s+mim\s+)?(?:o\s+)?(?:que\s+)?(?:tem\s+)?'
            rf'(?:em|na|no|nesse|nessa)\s+["\']?(.+?)["\']?$',
            text, re.I,
        )
        if m:
            raw = m.group(1).strip()
            if raw and not re.search(r'(?:arquivo|documento|conteudo)', raw):
                return self._exec("list_files", {"path": self._parse_path(raw)})

        # "lista X" (single word path)
        m = re.search(r'^(?:listar?|lista)\s+["\']?(\S+)["\']?$', text.strip(), re.I)
        if m:
            return self._exec("list_files", {"path": self._parse_path(m.group(1))})

        # ── "leia/abra a pasta/home/diretorio" → list_files
        if re.search(r'(?:ler|abra?|leia?|abrir)\s+(?:a\s+|o\s+)?(?:pastas?|home|diretorio)', lower):
            m = re.search(r'(?:ler|abra?|leia?|abrir)\s+(?:a\s+|o\s+)?(?:pastas?|home|diretorio)\s+(.+)?$', lower)
            path = m.group(1).strip() if m and m.group(1) else "~"
            return self._exec("list_files", {"path": self._parse_path(path)})

        # ── read file ─────────────────────────────────────
        if re.search(self._READ_VERBS, lower) \
                and (re.search(r'(?:arquivo|documento|texto|conteudo)', lower)
                     or re.search(r'(?:ler|abra?|leia?|abrir)\s+', lower)):
            m = re.search(
                rf'{self._READ_VERBS}\s+(?:o\s+)?(?:arquivo\s+)?(?:chamado\s+)?'
                rf'["\'](.+?)["\']',
                text, re.I,
            )
            if m:
                return self._exec("read_file", {"path": m.group(1).strip()})
            m = re.search(
                rf'{self._READ_VERBS}\s+(?:o\s+)?(?:arquivo\s+)?(?:chamado\s+)?'
                rf'(\S+)',
                text, re.I,
            )
            if m:
                path = m.group(1).strip()
                if not re.search(r'^(?:pastas?|home|diretorio|meu|minha|na|no|em|a\s+|o\s+)', path, re.I):
                    return self._exec("read_file", {"path": path})

        # ── write file ────────────────────────────────────
        # "cria/salva/escreve [um] arquivo X [com] Y"
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

        # "escreve EM/NO/NA X: Y"
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

        # ── fallback: assistente_local on, try as command ─
        if permitted:
            # git / mkdir / apt / pip etc
            if re.search(r'^(?:git|mkdir|touch|cp|mv|rm|apt|pip|npm|yarn|docker|make|cmake|sudo)\s', text.strip()):
                return self._exec("run_command", {"command": text.strip()})

        return None

    def _parse_path(self, raw):
        raw = raw.strip().rstrip(".,!?;:")
        if re.search(r'^(?:(?:minha\s+)?(?:home|pastas?(?:\s+home)?|diretorio)|meu\s+home)\s*$', raw, re.I):
            return "~"
        expanded = os.path.expanduser(raw)
        if os.path.exists(expanded):
            return expanded
        # case-insensitive fallback for Linux
        resolved = _resolve_ci(expanded)
        if resolved:
            return resolved
        # try as ~/raw
        if not raw.startswith("~") and not raw.startswith("/") and not raw.startswith("."):
            expanded = os.path.expanduser(f"~/{raw}")
            if os.path.exists(expanded):
                return expanded
            resolved = _resolve_ci(expanded)
            if resolved:
                return resolved
        return raw


    def _exec(self, tool_name, args):
        cfg = config.load()
        if not cfg.get("assistente_local", False):
            return "erro: assistente local desativado (clique direito na Teto e ative)"

        tool = TOOLS.get(tool_name)
        if not tool:
            return None

        try:
            result = tool["execute"](**args)
        except TypeError as e:
            return f"erro: argumentos inválidos pra {tool_name}: {e}"
        if tool_name == "screenshot":
            return f"screenshot: {result[:200]}"
        if tool_name == "run_command":
            print(f"[teto-pet] Comando: {args.get('command', '?')[:60]}", file=sys.stderr)
            return f"run_command: {result[:500]}"
        if tool_name == "write_file":
            print(f"[teto-pet] Arquivo: {args.get('path', '?')}", file=sys.stderr)
            return f"write_file: {result[:200]}"
        print(f"[teto-pet] {tool_name}: {result[:60]}", file=sys.stderr)
        return f"{tool_name}({args.get('path', '~')}): {result[:1000]}"

    def _on_send(self, _widget=None):
        text = self.entry.get_text().strip()
        if not text or self.waiting:
            return

        self.entry.set_text("")
        self._add_bubble("Você", text, "user")
        self.history.append({"role": "user", "content": text})

        tool_result = self._run_tool(text)

        self.waiting = True
        self.entry.set_sensitive(False)
        thinking_row = self._add_bubble("Teto", "…", "teto")

        user_mood = _detect_mood(text)

        def on_reply(reply):
            self.waiting = False
            self.entry.set_sensitive(True)

            self.history.append({"role": "assistant", "content": reply})
            _save_history(self.history)
            self.msg_list.remove(thinking_row)

            reply_mood = _detect_mood(reply)
            if reply_mood == Mood.NORMAL and user_mood != Mood.NORMAL:
                reply_mood = user_mood

            self._add_bubble("Teto", reply, "teto")
            self.emit("teto-speech", reply, reply_mood)

        if tool_result:
            ai.ask(text, self.history, callback=on_reply,
                   tool_context=tool_result)
        else:
            ai.ask(text, self.history, callback=on_reply)


def _resolve_ci(path):
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
