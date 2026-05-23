import math
import random

from gi.repository import Gtk, Gdk, GLib, cairo

from teto_pet import config
from teto_pet.character import Teto, Mood, FRAME_MS
from teto_pet.chat import ChatWindow
from teto_pet import phrases


class TetoPet(Gtk.Window):

    def __init__(self):
        super().__init__(title="Teto Pet")

        self.cfg = config.load()
        self.character = Teto()
        self.chat_window = None
        self.dragging = False
        self.drag_x = 0
        self.drag_y = 0
        self.offset_x = 0
        self.offset_y = 0
        self.speech_queue = []
        self.current_speech = None
        self.talking_timer = None

        fw = 128 // self.character.num_frames
        fh = 32
        scale = 5
        self.set_default_size(fw * scale, fh * scale + 40)
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
        )
        self.da.connect("button-press-event", self._on_button_press)
        self.da.connect("button-release-event", self._on_button_release)
        self.da.connect("motion-notify-event", self._on_motion)
        self.add(self.da)

        self.connect("destroy", self._on_destroy)

        self.show_all()
        GLib.timeout_add(FRAME_MS, self._anim_tick)
        GLib.timeout_add_seconds(45, self._random_speech)

    def _anim_tick(self):
        self.character.tick()
        self.da.queue_draw()
        return True

    def _random_speech(self):
        msgs = random.choice(list(phrases.FALLBACKS.values()))
        self.show_speech(random.choice(msgs))
        return True

    def show_speech(self, text, duration=3):
        self.speech_queue.append((text, duration))
        if self.talking_timer is None:
            self._show_next_speech()

    def _show_next_speech(self):
        if not self.speech_queue:
            self.talking_timer = None
            self.current_speech = None
            self.character.set_talking(False)
            self.da.queue_draw()
            return

        text, duration = self.speech_queue.pop(0)
        self.current_speech = text
        self.character.set_talking(True)
        self.da.queue_draw()

        self.talking_timer = GLib.timeout_add_seconds(
            duration, self._clear_speech
        )

    def _clear_speech(self):
        self.current_speech = None
        self.character.set_talking(False)
        self.da.queue_draw()
        GLib.idle_add(self._show_next_speech)
        return False

    def _on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        self.character.draw(cr, w, h - 20)
        self._draw_speech_bubble(cr, w)

        return False

    def _draw_speech_bubble(self, cr, win_w):
        if not self.current_speech:
            return

        text = self.current_speech
        cr.save()

        pad_x, pad_y = 12, 8
        max_width = win_w - 20
        cw = 6.5
        lines = []
        cur = ""
        for word in text.split():
            test = cur + (" " if cur else "") + word
            if len(test) * cw > max_width:
                lines.append(cur)
                cur = word
            else:
                cur = test
        if cur:
            lines.append(cur)

        lh = 16
        bub_w = max(min(max(len(l) for l in lines) * cw + pad_x * 2, max_width), 60)
        bub_h = len(lines) * lh + pad_y * 2 + 2
        bub_x = (win_w - bub_w) / 2
        bub_y = 2

        cr.set_source_rgba(1, 1, 1, 0.92)
        cr.move_to(bub_x + 8, bub_y)
        cr.arc(bub_x + bub_w - 8, bub_y + 8, 8, -math.pi / 2, 0)
        cr.arc(bub_x + bub_w - 8, bub_y + bub_h - 8, 8, 0, math.pi / 2)
        cr.arc(bub_x + 8, bub_y + bub_h - 8, 8, math.pi / 2, math.pi)
        cr.arc(bub_x + 8, bub_y + 8, 8, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill_preserve()
        cr.set_source_rgba(0.7, 0.7, 0.7, 0.4)
        cr.set_line_width(1)
        cr.stroke()

        cr.set_source_rgba(0.1, 0.1, 0.1, 0.95)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(12)
        for i, line in enumerate(lines):
            cr.move_to(bub_x + pad_x, bub_y + pad_y + i * lh + 12)
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

        self.chat_window.connect("teto-speech", self._on_chat_speech)
        self.chat_window.show_all()

    def _on_chat_speech(self, _win, text, mood):
        if mood:
            self.character.set_mood(mood)
        self.show_speech(text)

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

    def _on_destroy(self, _w=None):
        x, y = self.get_position()
        self.cfg["window_x"] = x
        self.cfg["window_y"] = y
        config.save(self.cfg)
        Gtk.main_quit()
