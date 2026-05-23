from gi.repository import Gtk, Pango

from teto_pet import ai


class ChatWindow(Gtk.Window):

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
        self._add_bubble("Teto", "Oii! Que bom te ver! ^_^", "teto")

    def _add_bubble(self, who, text, cls):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(spacing=4)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)

        label = Gtk.Label()
        label.set_markup(
            f"<b>{who}:</b>  {text}"
        )
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

    def _on_send(self, _widget=None):
        text = self.entry.get_text().strip()
        if not text:
            return

        self.entry.set_text("")
        self._add_bubble("Você", text, "user")

        self.history.append({"role": "user", "content": text})

        reply = ai.ask(text, self.history)

        self.history.append({"role": "assistant", "content": reply})
        self._add_bubble("Teto", reply, "teto")
