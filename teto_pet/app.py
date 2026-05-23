import math

from gi.repository import Gtk, Gdk, GLib, cairo

from teto_pet import config
from teto_pet.character import Teto
from teto_pet.chat import ChatWindow
from teto_pet import phrases


class TetoPet(Gtk.Window):

    def __init__(self):
        super().__init__(title="Teto Pet")

        self.cfg = config.load()
        self.character = Teto()
        self.chat_window = None
        self.speech_timer = None
        self.dragging = False
        self.drag_x = 0
        self.drag_y = 0
        self.offset_x = 0
        self.offset_y = 0
        self.speech_queue = []
        self.current_speech = None

        win_w = min(220, int(350 * self.character.aspect))
        win_h = min(int(win_w / self.character.aspect), 600)
        self.set_default_size(win_w, win_h)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_keep_above(self.cfg.get("always_on_top", True))
        self.set_skip_taskbar_hint(True)
        self.move(self.cfg.get("window_x", 100), self.cfg.get("window_y", 100))

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)



        self.da = Gtk.DrawingArea()
        self.da.connect("draw", self._on_draw)
        self.da.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
        )
        self.da.connect("button-press-event", self._on_button_press)
        self.da.connect("button-release-event", self._on_button_release)
        self.da.connect("motion-notify-event", self._on_motion)
        self.add(self.da)

        self.connect("destroy", self._on_destroy)

        self._start_idle()
        self.show_all()

        GLib.idle_add(self._say_random_greeting)

    def _say_random_greeting(self):
        GLib.timeout_add_seconds(45, self._random_speech)
        return False

    def _random_speech(self):
        import random
        msg = random.choice(list(phrases.FALLBACKS.values()))
        self.show_speech(random.choice(msg))
        return True

    def show_speech(self, text, duration=4):
        self.speech_queue.append((text, duration))
        if self.speech_timer is None:
            self._show_next_speech()

    def _show_next_speech(self):
        if not self.speech_queue:
            self.speech_timer = None
            self.da.queue_draw()
            return

        text, duration = self.speech_queue.pop(0)
        self.current_speech = text
        self.speech_opacity = 1.0
        self.da.queue_draw()

        self.speech_timer = GLib.timeout_add_seconds(
            duration, self._clear_speech
        )

    def _clear_speech(self):
        self.current_speech = None
        self.speech_opacity = 0
        self.da.queue_draw()
        GLib.idle_add(self._show_next_speech)
        return False

    def _on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        self.character.draw(cr, w, h - 30)

        self._draw_speech_bubble(cr, w)

        GLib.timeout_add(50, self._redraw_loop)
        return False

    def _redraw_loop(self):
        self.da.queue_draw()
        return False

    def _draw_speech_bubble(self, cr, win_w):
        if not hasattr(self, "current_speech") or not self.current_speech:
            return

        text = self.current_speech

        cr.save()

        pad_x, pad_y = 14, 10
        max_width = win_w - 24
        char_width = 7
        lines = []
        current_line = ""
        for word in text.split():
            test = current_line + (" " if current_line else "") + word
            if len(test) * char_width > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        line_height = 18
        bub_w = max(min(len(l) * char_width + pad_x * 2, max_width), 80)
        bub_h = len(lines) * line_height + pad_y * 2 + 4
        bub_x = (win_w - bub_w) / 2
        bub_y = 4

        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.move_to(bub_x + 10, bub_y)
        cr.arc(bub_x + bub_w - 10, bub_y + 10, 10, -math.pi / 2, 0)
        cr.arc(bub_x + bub_w - 10, bub_y + bub_h - 10, 10, 0, math.pi / 2)
        cr.arc(bub_x + 10, bub_y + bub_h - 10, 10, math.pi / 2, math.pi)
        cr.arc(bub_x + 10, bub_y + 10, 10, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill_preserve()
        cr.set_source_rgba(0.8, 0.8, 0.8, 0.5)
        cr.set_line_width(1)
        cr.stroke()

        cr.set_source_rgba(0.1, 0.1, 0.1, 0.95)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(13)
        for i, line in enumerate(lines):
            cr.move_to(bub_x + pad_x, bub_y + pad_y + i * line_height + 14)
            cr.show_text(line)

        cr.restore()

    def _on_button_press(self, _w, ev):
        if ev.button == 1:
            self.dragging = True
            self.drag_x, self.drag_y = int(ev.x_root), int(ev.y_root)
            x, y = self.get_position()
            self.offset_x = x - self.drag_x
            self.offset_y = y - self.drag_y
        elif ev.button == 3:
            self._show_context_menu(ev)
        return True

    def _on_button_release(self, _w, ev):
        if ev.button == 1:
            self.dragging = False
            x, y = self.get_position()
            self.cfg["window_x"] = x
            self.cfg["window_y"] = y
            config.save(self.cfg)
        return True

    def _on_motion(self, _w, ev):
        if self.dragging:
            self.move(
                int(ev.x_root) + self.offset_x,
                int(ev.y_root) + self.offset_y,
            )
        return True

    def _show_context_menu(self, ev):
        menu = Gtk.Menu()

        chat_item = Gtk.MenuItem.new_with_label("Conversar")
        chat_item.connect("activate", lambda _: self._open_chat())
        menu.append(chat_item)

        menu.append(Gtk.SeparatorMenuItem())

        top_item = Gtk.CheckMenuItem.new_with_label("Sempre no topo")
        top_item.set_active(self.cfg.get("always_on_top", True))
        top_item.connect("toggled", self._toggle_ontop)
        menu.append(top_item)

        ai_item = Gtk.CheckMenuItem.new_with_label("Usar IA local")
        ai_item.set_active(self.cfg.get("ai_enabled", False))
        ai_item.connect("toggled", self._toggle_ai)
        menu.append(ai_item)

        menu.append(Gtk.SeparatorMenuItem())

        about_item = Gtk.MenuItem.new_with_label("Sobre")
        about_item.connect("activate", self._show_about)
        menu.append(about_item)

        quit_item = Gtk.MenuItem.new_with_label("Sair")
        quit_item.connect("activate", lambda _: self._on_destroy())
        menu.append(quit_item)

        menu.show_all()
        menu.popup_at_pointer(ev)

    def _open_chat(self):
        if self.chat_window is not None:
            self.chat_window.present()
            return
        self.chat_window = ChatWindow(self)
        self.chat_window.connect("destroy", self._on_chat_closed)
        self.chat_window.show_all()

    def _on_chat_closed(self, _w=None):
        self.chat_window = None

    def _toggle_ontop(self, item):
        self.cfg["always_on_top"] = item.get_active()
        self.set_keep_above(item.get_active())
        config.save(self.cfg)

    def _toggle_ai(self, item):
        self.cfg["ai_enabled"] = item.get_active()
        config.save(self.cfg)

    def _show_about(self, _item=None):
        about = Gtk.AboutDialog()
        about.set_program_name("Teto Pet")
        about.set_version("0.1.0")
        about.set_comments("Um pet virtual da Kasane Teto")
        about.set_copyright("MCookinho")
        about.set_license("MIT")
        about.set_transient_for(self)
        about.run()
        about.destroy()

    def _start_idle(self):
        GLib.timeout_add_seconds(5, self._idle_bounce)

    def _idle_bounce(self):
        self.idle_animation = (self.idle_animation + 1) % 2
        return True

    def _on_destroy(self, _w=None):
        x, y = self.get_position()
        self.cfg["window_x"] = x
        self.cfg["window_y"] = y
        config.save(self.cfg)
        Gtk.main_quit()
