import math
import random

import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, cairo

from teto_pet import config
from teto_pet.character import Teto, Mood, FRAME_MS
from teto_pet.chat import ChatWindow
from teto_pet import phrases


CHAR_SCALE = 5
CHAR_X = 16
CHAR_Y = 20
BUBBLE_X = 180
BUBBLE_W = 190
BUBBLE_PAD = 12
BUBBLE_MARGIN = 8
WIN_W = BUBBLE_X + BUBBLE_W + BUBBLE_MARGIN
WIN_H = 32 * CHAR_SCALE + 50


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

        self.set_default_size(WIN_W, WIN_H)
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

        self.character.draw(cr, w, h, dx=CHAR_X, dy=CHAR_Y)
        self._draw_speech_bubble(cr, w)

        return True

    def _draw_speech_bubble(self, cr, win_w):
        if not self.current_speech:
            return

        text = self.current_speech
        cr.save()

        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        fd = Pango.FontDescription("Pixelify Sans 13")
        layout.set_font_description(fd)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_width(int(BUBBLE_W * Pango.SCALE))

        ink, logical = layout.get_pixel_extents()
        bw = max(logical.width + BUBBLE_PAD * 2, 60)
        bh = logical.height + BUBBLE_PAD * 2 + 6
        bx = BUBBLE_X
        by = CHAR_Y

        cr.set_source_rgba(1, 1, 1, 0.92)
        r = 8
        cr.move_to(bx + r, by)
        cr.arc(bx + bw - r, by + r, r, -math.pi / 2, 0)
        cr.arc(bx + bw - r, by + bh - r, r, 0, math.pi / 2)
        cr.arc(bx + r, by + bh - r, r, math.pi / 2, math.pi)
        cr.arc(bx + r, by + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill_preserve()
        cr.set_source_rgba(0.7, 0.7, 0.7, 0.4)
        cr.set_line_width(1)
        cr.stroke()

        tail_cy = by + bh / 2
        cr.move_to(bx, tail_cy - 6)
        cr.line_to(bx - 10, tail_cy)
        cr.line_to(bx, tail_cy + 6)
        cr.close_path()
        cr.set_source_rgba(1, 1, 1, 0.92)
        cr.fill()

        cr.set_source_rgba(0.1, 0.1, 0.1, 0.95)
        cr.move_to(bx + BUBBLE_PAD, by + BUBBLE_PAD + 2)
        PangoCairo.show_layout(cr, layout)

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
