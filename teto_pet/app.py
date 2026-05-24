import math
import os
import random
import sys

import requests

import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, cairo

from teto_pet import config
from teto_pet.models import model, list_models
from teto_pet.character import Teto, Mood, FRAME_MS
from teto_pet.chat import ChatWindow
from teto_pet import phrases, ai
from teto_pet.ai import ollama_ensure_running, ollama_stop
from teto_pet.tools import screenshot as _screenshot_fn


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
        super().__init__(title="Mate Helper")

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
        self._accessibility_timer_id = None
        self._accessibility_busy = False
        self._start_accessibility_timer()

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

    def _start_accessibility_timer(self):
        self._stop_accessibility_timer()
        if self.cfg.get("accessibility_enabled", False):
            interval = max(5, self.cfg.get("accessibility_interval", 30))
            self._accessibility_timer_id = GLib.timeout_add_seconds(interval, self._accessibility_tick)
            print(f"[mate-helper] Acessibilidade: timer ligado ({interval}s)", file=sys.stderr)

    def _stop_accessibility_timer(self):
        if self._accessibility_timer_id is not None:
            GLib.source_remove(self._accessibility_timer_id)
            self._accessibility_timer_id = None

    def _accessibility_tick(self):
        if not self.cfg.get("accessibility_enabled", False):
            return False
        if self._accessibility_busy:
            return True
        img = _screenshot_fn()
        if img and not img.startswith("erro") and not img.startswith("Não"):
            self._accessibility_busy = True
            def on_reply(reply):
                self._accessibility_busy = False
                if reply:
                    self.show_speech(reply, 4)
            ai.ask(
                "De uma olhada na tela do usuário e comente naturalmente como amiga "
                "o que você vê. Seja breve e direta, como se estivesse olhando junto com ele.",
                history=[],
                callback=on_reply,
                image_base64=img,
            )
        return True

    def _toggle_accessibility(self, item):
        self.cfg["accessibility_enabled"] = item.get_active()
        config.save(self.cfg)
        if item.get_active():
            self._start_accessibility_timer()
        else:
            self._stop_accessibility_timer()

    def _setup_accessibility_interval(self, _item=None):
        dialog = Gtk.Dialog(
            title="Intervalo da leitura automática",
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Ok", Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label(label="A cada quantos segundos a tela deve ser lida?")
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        adj = Gtk.Adjustment(
            value=self.cfg.get("accessibility_interval", 30),
            lower=5, upper=300, step_increment=5,
        )
        spin = Gtk.SpinButton(adjustment=adj)
        spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_enabled", False):
                self._start_accessibility_timer()
        dialog.destroy()

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

        side = self.cfg.get("bubble_side", config.BUBBLE_AUTO)
        if side == config.BUBBLE_LEFT:
            on_right = False
        elif side == config.BUBBLE_RIGHT:
            on_right = True
        else:
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
        fd = Pango.FontDescription(f"{model.FONT_NAME} {model.FONT_SIZE}")
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

        # ── Interação ──────────────────────────────
        chat_item = Gtk.MenuItem.new_with_label("Conversar")
        chat_item.connect("activate", lambda _: self._open_chat())
        menu.append(chat_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Aparência ──────────────────────────────
        appear_menu = Gtk.Menu()
        appear_sub = Gtk.MenuItem.new_with_label("Aparência")
        appear_sub.set_submenu(appear_menu)

        top_item = Gtk.CheckMenuItem.new_with_label("Sempre no topo")
        top_item.set_active(self.cfg.get("always_on_top", True))
        top_item.connect("toggled", self._toggle_ontop)
        appear_menu.append(top_item)

        bubble_menu = Gtk.Menu()
        bubble_sub = Gtk.MenuItem.new_with_label("Lado do balão")
        bubble_sub.set_submenu(bubble_menu)
        current_side = self.cfg.get("bubble_side", config.BUBBLE_AUTO)
        group_side = []
        for key, label in [
            (config.BUBBLE_AUTO, "Automático"),
            (config.BUBBLE_LEFT, "Esquerda"),
            (config.BUBBLE_RIGHT, "Direita"),
        ]:
            item = Gtk.RadioMenuItem.new_with_label(group_side, label)
            if key == current_side:
                item.set_active(True)
            item.connect("activate", self._change_bubble_side, key)
            bubble_menu.append(item)
            group_side = [item]
        appear_menu.append(bubble_sub)

        model_menu = Gtk.Menu()
        model_sub = Gtk.MenuItem.new_with_label("Modelo do pet")
        model_sub.set_submenu(model_menu)
        current_model = self.cfg.get("active_model", "kasane_teto")
        group_model = []
        for m in list_models():
            label = m.replace("_", " ").title()
            item = Gtk.RadioMenuItem.new_with_label(group_model, label)
            if m == current_model:
                item.set_active(True)
            item.connect("activate", self._change_model, m)
            model_menu.append(item)
            group_model = [item]
        appear_menu.append(model_sub)

        menu.append(appear_sub)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Acessibilidade ──────────────────────────
        acc_menu = Gtk.Menu()
        acc_sub = Gtk.MenuItem.new_with_label("Acessibilidade")
        acc_sub.set_submenu(acc_menu)

        acc_item = Gtk.CheckMenuItem.new_with_label("Leitura automática da tela")
        acc_item.set_active(self.cfg.get("accessibility_enabled", False))
        acc_item.connect("toggled", self._toggle_accessibility)
        acc_menu.append(acc_item)

        interval_item = Gtk.MenuItem.new_with_label("Intervalo...")
        interval_item.connect("activate", self._setup_accessibility_interval)
        acc_menu.append(interval_item)

        menu.append(acc_sub)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Inteligência ──────────────────────────
        ai_menu = Gtk.Menu()
        ai_sub = Gtk.MenuItem.new_with_label("Inteligência")
        ai_sub.set_submenu(ai_menu)

        provider_menu = Gtk.Menu()
        provider_sub = Gtk.MenuItem.new_with_label("Provedor de IA")
        provider_sub.set_submenu(provider_menu)
        current = self.cfg.get("ai_provider", config.PROVIDER_AUTO)
        group_prov = []
        for key, label in [
            (config.PROVIDER_AUTO, "Automático"),
            (config.PROVIDER_GROQ, "Groq (grátis)"),
            (config.PROVIDER_GEMINI, "Gemini (Google)"),
            (config.PROVIDER_HF, "API (Hugging Face)"),
            (config.PROVIDER_OLLAMA, "Ollama (local)"),
            (config.PROVIDER_PHRASES, "Frases prontas"),
        ]:
            item = Gtk.RadioMenuItem.new_with_label(group_prov, label)
            if key == current:
                item.set_active(True)
            item.connect("activate", self._change_provider, key)
            provider_menu.append(item)
            group_prov = [item]
        ai_menu.append(provider_sub)

        gemini_setup = Gtk.MenuItem.new_with_label("Configurar Gemini...")
        gemini_setup.connect("activate", lambda _: self._setup_gemini())
        ai_menu.append(gemini_setup)

        groq_setup = Gtk.MenuItem.new_with_label("Configurar Groq...")
        groq_setup.connect("activate", lambda _: self._setup_groq())
        ai_menu.append(groq_setup)

        ollama_models = self._list_ollama_models()
        if ollama_models:
            model_menu = Gtk.Menu()
            model_sub = Gtk.MenuItem.new_with_label("Modelo Ollama")
            model_sub.set_submenu(model_menu)
            current_om = self.cfg.get("ollama_model", "")
            group_om = []
            for m in ollama_models:
                label = m
                item = Gtk.RadioMenuItem.new_with_label(group_om, label)
                if m == current_om or (not current_om and group_om == []):
                    item.set_active(True)
                item.connect("activate", self._change_ollama_model, m)
                model_menu.append(item)
                group_om = [item]
            ai_menu.append(model_sub)

        ai_menu.append(Gtk.SeparatorMenuItem())

        tools_menu = Gtk.Menu()
        tools_sub = Gtk.MenuItem.new_with_label("Permissões")
        tools_sub.set_submenu(tools_menu)
        for key, label in [
            ("tool_read_file", "Ler arquivos"),
            ("tool_list_files", "Listar pastas"),
            ("tool_run_command", "Executar comandos"),
            ("tool_write_file", "Escrever arquivos"),
            ("tool_screenshot", "Capturar tela"),
            ("tool_open_url", "Abrir URLs"),
        ]:
            item = Gtk.CheckMenuItem.new_with_label(label)
            item.set_active(self.cfg.get(key, False))
            item.connect("toggled", self._toggle_tool, key)
            tools_menu.append(item)
        ai_menu.append(tools_sub)

        menu.append(ai_sub)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Ações ─────────────────────────────────
        profile_item = Gtk.MenuItem.new_with_label("Meu Perfil...")
        profile_item.connect("activate", lambda _: self._setup_profile())
        menu.append(profile_item)

        clear_item = Gtk.MenuItem.new_with_label("Limpar Histórico")
        clear_item.connect("activate", self._clear_history)
        menu.append(clear_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Sistema ───────────────────────────────
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

    def _clear_history(self, _item=None):
        if self.chat_window is not None:
            self.chat_window.clear_history()
        else:
            try:
                os.remove(os.path.expanduser("~/.config/teto-pet/chat_history.json"))
            except OSError:
                pass

    def _toggle_ontop(self, item):
        self.cfg["always_on_top"] = item.get_active()
        self.set_keep_above(item.get_active())
        config.save(self.cfg)

    def _toggle_tool(self, item, key):
        self.cfg[key] = item.get_active()
        config.save(self.cfg)

    def _change_bubble_side(self, item, side):
        if item.get_active():
            self.cfg["bubble_side"] = side
            config.save(self.cfg)
            self.da.queue_draw()

    def _change_model(self, item, model_name):
        if item.get_active():
            self.cfg["active_model"] = model_name
            config.save(self.cfg)
            self.character.reload_sprites()
            self.da.queue_draw()
            self.show_speech(f"Modelo trocado pra {model_name.replace('_', ' ').title()}! ^_^")

    def _setup_gemini(self):
        dialog = Gtk.Dialog(
            title="Configurar Gemini",
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Salvar", Gtk.ResponseType.OK)
        dialog.set_default_size(400, 200)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(
            "<b>Gemini API Key</b>\n\n"
            "O Gemini tem um plano gratuito generoso (60 req/min).\n\n"
            "1. Acesse: https://aistudio.google.com/apikey\n"
            "2. Clique em \"Criar chave de API\"\n"
            "3. Copie a chave e cole abaixo\n\n"
            "Não precisa de cartão de crédito."
        )
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Cole sua chave Gemini aqui...")
        entry.set_text(self.cfg.get("gemini_key", ""))
        entry.set_visibility(False)
        area.pack_start(entry, False, False, 6)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://aistudio.google.com/apikey",
            "Abrir Google AI Studio",
        )
        area.pack_start(link_btn, False, False, 6)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            key = entry.get_text().strip()
            if key:
                self.cfg["gemini_key"] = key
                config.save(self.cfg)
                self.show_speech("Gemini configurado! Vou usar IA do Google! ^_^")
            else:
                self.show_speech("Não colou nenhuma chave... Tenta de novo!")
        dialog.destroy()

    def _setup_groq(self):
        dialog = Gtk.Dialog(
            title="Configurar Groq",
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Salvar", Gtk.ResponseType.OK)
        dialog.set_default_size(400, 220)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(
            "<b>Groq API Key</b>\n\n"
            "Groq é 100% gratuito e MUITO rápido!\n"
            "Usa GPU própria (LPU) pra rodar Llama 3, Gemma e Mixtral.\n\n"
            "1. Acesse: https://console.groq.com/keys\n"
            "2. Clique em \"Create API Key\"\n"
            "3. Copie a chave e cole abaixo\n\n"
            "Não precisa de cartão de crédito. ~600 req/dia grátis!"
        )
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Cole sua chave Groq aqui...")
        entry.set_text(self.cfg.get("groq_key", ""))
        entry.set_visibility(False)
        area.pack_start(entry, False, False, 6)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://console.groq.com/keys",
            "Abrir Groq Console",
        )
        area.pack_start(link_btn, False, False, 6)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            key = entry.get_text().strip()
            if key:
                self.cfg["groq_key"] = key
                config.save(self.cfg)
                self.show_speech("Groq configurado! Vou usar a IA mais rápida! ^_^")
            else:
                self.show_speech("Não colou nenhuma chave... Tenta de novo!")
        dialog.destroy()

    def _list_ollama_models(self):
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                return sorted(m["name"] for m in resp.json().get("models", []))
        except Exception:
            pass
        return []

    def _change_ollama_model(self, item, model_name):
        if item.get_active():
            self.cfg["ollama_model"] = model_name
            config.save(self.cfg)

    def _change_provider(self, item, provider):
        if item.get_active():
            self.cfg["ai_provider"] = provider
            config.save(self.cfg)
            if provider == config.PROVIDER_GEMINI and not self.cfg.get("gemini_key"):
                GLib.idle_add(self._setup_gemini)
            if provider == config.PROVIDER_GROQ and not self.cfg.get("groq_key"):
                GLib.idle_add(self._setup_groq)
            if provider in (config.PROVIDER_AUTO, config.PROVIDER_OLLAMA):
                GLib.idle_add(lambda: ollama_ensure_running())

    def _setup_profile(self):
        dialog = Gtk.Dialog(
            title="Meu Perfil",
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons("Cancelar", Gtk.ResponseType.CANCEL, "Salvar", Gtk.ResponseType.OK)
        dialog.set_default_size(360, 260)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup("<b>Como a IA deve te tratar</b>\n\n"
                       "Esses dados são salvos localmente e usados\n"
                       "apenas para a IA te conhecer melhor.")
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        name_lbl = Gtk.Label(label="Seu nome:")
        name_lbl.set_xalign(0)
        area.pack_start(name_lbl, False, False, 2)

        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("Ex: João, Maria...")
        name_entry.set_text(self.cfg.get("user_name", ""))
        area.pack_start(name_entry, False, False, 4)

        bio_lbl = Gtk.Label(label="Detalhes extras (opcional):")
        bio_lbl.set_xalign(0)
        area.pack_start(bio_lbl, False, False, 2)

        bio_entry = Gtk.Entry()
        bio_entry.set_placeholder_text("Ex: pronomes, idade, apelido...")
        bio_entry.set_text(self.cfg.get("user_bio", ""))
        area.pack_start(bio_entry, False, False, 4)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            name = name_entry.get_text().strip()
            bio = bio_entry.get_text().strip()
            self.cfg["user_name"] = name
            self.cfg["user_bio"] = bio
            config.save(self.cfg)
            if name:
                self.show_speech(f"Anotado! Vou te chamar de {name} agora! ^_^")
            else:
                self.show_speech("Perfil atualizado! ^_^")
        dialog.destroy()

    def _show_about(self, _item=None):
        about = Gtk.AboutDialog()
        about.set_program_name("Mate Helper")
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
        self._stop_accessibility_timer()
        ollama_stop()
        Gtk.main_quit()
