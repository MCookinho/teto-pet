import os
import re

from gi.repository import Gtk, Pango, GObject

from teto_pet import ai, config
from teto_pet.character import Mood
from teto_pet.tools import TOOLS, TOOL_KEYWORDS


def _detect_mood(text):
    words = set(text.lower().split())
    if words & {"triste", "chateado", "chateada", "depre", "mal", "ruim", "tristeza", "sorry", "desculpa"}:
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

        self.history = []
        self.waiting = False
        self._add_bubble("Teto", "Oii! Que bom te ver! ^_^", "teto")

    def _add_bubble(self, who, text, cls):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(spacing=4)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        label = Gtk.Label()
        label.set_markup(f"<b>{who}:</b>  {text}")
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
        # "o que tem [em/na/no] X" (NOT arquivo)
        if re.search(r'(?:o\s+)?(?:que|q)\s+tem\s+(?:em|na|no)\s+', lower) \
                and not re.search(r'(?:arquivo|documento|texto|conteudo)\s', lower):
            m = re.search(r'(?:o\s+)?(?:que|q)\s+tem\s+(?:em|na|no)\s+(.+)', lower, re.I)
            if m:
                return self._exec("list_files", {"path": self._parse_path(m.group(1))})

        # "veja/lista/mostra [a/o] [minha/meu] pasta/home/diretorio"
        if re.search(rf'{self._LIST_VERBS}\s+', lower) \
                and re.search(r'(?:pasta|home|diretorio|dir|area)', lower) \
                and not re.search(r'(?:arquivo|documento|texto|conteudo)', lower):
            m = re.search(r'(?:pasta|home|diretorio|dir|area(?:\s+de\s+trabalho)?)\s*(.+)?$', lower, re.I)
            path = m.group(1).strip() if m and m.group(1) else "~"
            return self._exec("list_files", {"path": path})

        # "minha pasta", "meu home", "pasta home"
        if re.search(r'(?:minha\s+pasta|meu\s+home|pasta\s+home)', lower) \
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
                if not re.search(r'^(?:pasta|home|diretorio|meu|minha|na|no|em|a\s+|o\s+)', path, re.I):
                    return self._exec("read_file", {"path": path})

        # ── fallback: any mention of home/pasta/arquivo ──
        if re.search(r'\b(?:home|pasta|diretorio|arquivo)\b', lower):
            path = "~" if re.search(r'(?:home|pasta|diretorio)', lower) else None
            if path:
                return self._exec("list_files", {"path": path})

        return None

    def _parse_path(self, raw):
        raw = raw.strip().rstrip(".,!?;:")
        if re.search(r'^(?:(?:minha\s+)?(?:home|pasta(\s+home)?|diretorio)|meu\s+home)\s*$', raw, re.I):
            return "~"
        if raw.startswith("~") or raw.startswith("/") or raw.startswith("."):
            return raw
        return os.path.expanduser(f"~/{raw}") if "/" not in raw and "\\" not in raw else raw

    def _exec(self, tool_name, args):
        cfg = config.load()
        if not cfg.get("assistente_local", False):
            return "erro: assistente local desativado (clique direito na Teto e ative)"

        tool = TOOLS.get(tool_name)
        if not tool:
            return None

        result = tool["execute"](**args)
        if tool_name == "screenshot":
            return f"screenshot: {result[:200]}"
        return f"{tool_name}({args.get('path', '~')}): {result}"

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
