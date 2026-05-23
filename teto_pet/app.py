import math
import random

import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, cairo

from teto_pet import config
from teto_pet.character import Teto, Mood, FRAME_MS
from teto_pet.chat import ChatWindow
from teto_pet import phrases
from teto_pet.ai import ollama_ensure_running, ollama_stop


CHAR_SCALE = 5
CHAR_Y = 20
BUBBLE_W = 190
BUBBLE_PAD = 12
GAP = 16
MARGIN = 16
CHAR_W = 32 * CHAR_SCALE
BUBBLE_MAX = BUBBLE_W + BUBBLE_PAD * 2
WIN_W = MARGIN + CHAR_W + GAP + BUBBLE_MAX + MARGIN
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
        self._last_click_time = 0

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

        provider = self.cfg.get("ai_provider", config.PROVIDER_AUTO)
        if provider in (config.PROVIDER_AUTO, config.PROVIDER_OLLAMA):
            GLib.idle_add(self._start_ollama_if_needed)

        GLib.idle_add(lambda: self.show_speech("Oii! Que bom te ver! ^_^", 5))
        GLib.timeout_add_seconds(45, self._random_speech)

    def _start_ollama_if_needed(self):
        if ollama_ensure_running():
            self.show_speech("Ollama ligado! Tô pronta pra conversar! ^_^")
        else:
            self.show_speech("Hmm, não achei o Ollama... Vou usar frases prontas mesmo!")
        return False

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

    def _get_layout(self):
        wx, _ = self.get_position()
        screen = self.get_screen()
        sw = screen.get_width()
        on_right = (wx + WIN_W // 2) > (sw // 2)

        if on_right:
            char_x = WIN_W - CHAR_W - MARGIN
            bubble_x = MARGIN
            tail_dir = 1
        else:
            char_x = MARGIN
            bubble_x = MARGIN + CHAR_W + GAP
            tail_dir = -1

        return char_x, bubble_x, tail_dir

    def _on_draw(self, widget, cr):
        w, h = widget.get_allocated_width(), widget.get_allocated_height()
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        char_x, bubble_x, tail_dir = self._get_layout()

        self.character.draw(cr, w, h, dx=char_x, dy=CHAR_Y)
        self._draw_speech_bubble(cr, bubble_x, tail_dir)

        return True

    def _draw_speech_bubble(self, cr, bx, tail_dir):
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
        cr.move_to(bx if tail_dir > 0 else bx + bw, tail_cy - 6)
        cr.line_to(bx + tail_dir * 12, tail_cy)
        cr.line_to(bx if tail_dir > 0 else bx + bw, tail_cy + 6)
        cr.close_path()
        cr.set_source_rgba(1, 1, 1, 0.92)
        cr.fill()

        cr.set_source_rgba(0.1, 0.1, 0.1, 0.95)
        cr.move_to(bx + BUBBLE_PAD, by + BUBBLE_PAD + 2)
        PangoCairo.show_layout(cr, layout)

        cr.restore()

    def _on_button_press(self, _w, ev):
        if ev.button == 1:
            now = ev.time
            if now - self._last_click_time < 500:
                self._open_chat()
                self._last_click_time = 0
                return True
            self._last_click_time = now
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

        ai_menu = Gtk.Menu()
        ai_sub = Gtk.MenuItem.new_with_label("Provedor de IA")
        ai_sub.set_submenu(ai_menu)

        current = self.cfg.get("ai_provider", config.PROVIDER_AUTO)
        group = []
        for key, label in [
            (config.PROVIDER_AUTO, "Automático"),
            (config.PROVIDER_OLLAMA, "Ollama (local)"),
            (config.PROVIDER_HF, "API (Hugging Face)"),
            (config.PROVIDER_GEMINI, "Gemini (Google)"),
            (config.PROVIDER_PHRASES, "Frases prontas"),
        ]:
            item = Gtk.RadioMenuItem.new_with_label(group, label)
            if key == current:
                item.set_active(True)
            item.connect("activate", self._change_provider, key)
            ai_menu.append(item)
            group = [item]

        menu.append(ai_sub)

        local_item = Gtk.CheckMenuItem.new_with_label("Assistente Local")
        local_item.set_active(self.cfg.get("assistente_local", False))
        local_item.connect("toggled", self._toggle_assistente)
        menu.append(local_item)

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

    def _toggle_assistente(self, item):
        self.cfg["assistente_local"] = item.get_active()
        config.save(self.cfg)
        if item.get_active():
            self.show_speech("Assistente Local ativado! Posso ler arquivos e ver a tela! ^_^")
        else:
            self.show_speech("Assistente Local desativado. Só vou conversar mesmo!")

    def _change_provider(self, item, provider):
        if item.get_active():
            self.cfg["ai_provider"] = provider
            config.save(self.cfg)
            if provider in (config.PROVIDER_AUTO, config.PROVIDER_OLLAMA):
                GLib.idle_add(lambda: ollama_ensure_running())

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
        ollama_stop()
        Gtk.main_quit()
