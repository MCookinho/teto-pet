import math
import os
import random
import re
import socket
import subprocess
import sys
import threading

import requests

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo, cairo

from desktop_pet import config, ai
from desktop_pet.log import log
from desktop_pet.models import model, list_models

from desktop_pet.character import Teto, Mood, FRAME_MS
from desktop_pet.chat import ChatWindow
from desktop_pet.ai import ollama_ensure_running, ollama_stop
from desktop_pet.tools import screenshot as _screenshot_fn, listen as _listen_fn, listen_mic, list_mic_sources
from desktop_pet import tts as tts_mod
from desktop_pet import libras


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
        self._task_timers = []
        self._task_busy = {"screen": False, "audio": False}
        self._alarm_timer_id = None
        self._alarm_process = None
        self._alarm_ringing = False
        self._alarm_fired_today = set()
        self._mic_listener_timer = None
        self._mic_listening = False
        self._stt_shortcut_stop_event = None
        self._global_hotkey_listener = None
        self._global_keys_state = set()
        self._global_recording = False
        self._ptt_socket_path = os.path.expanduser("~/.cache/mate-helper-ptt.sock")
        self._ptt_helper_path = os.path.expanduser("~/.local/bin/mate-helper-ptt")
        os.makedirs(os.path.dirname(self._ptt_socket_path), exist_ok=True)
        self._start_ptt_socket_server()
        self._start_all_timers()
        self._start_alarm_check()
        GLib.idle_add(self._start_mic_listener)

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
        self.connect("key-press-event", self._on_key_press)
        self.connect("key-release-event", self._on_key_release)

        self.show_all()
        GLib.timeout_add(FRAME_MS, self._anim_tick)

        provider = self.cfg.get("ai_provider", config.PROVIDER_AUTO)
        if provider in (config.PROVIDER_AUTO, config.PROVIDER_OLLAMA):
            GLib.idle_add(self._start_ollama_if_needed)

        GLib.idle_add(lambda: self.show_speech(model.phrases.pick("GREETING", self._("greeting")), 5))
        GLib.idle_add(self._setup_global_hotkey)

    def _(self, key, **kwargs):
        return model.get_string(self.cfg.get("language", "pt"), key, **kwargs)

    def _start_ollama_if_needed(self):
        if ollama_ensure_running():
            self.show_speech(model.phrases.pick("OLLAMA_STARTED", self._("ollama_started")))
        else:
            self.show_speech(model.phrases.pick("OLLAMA_NOT_FOUND", self._("ollama_not_found")))
        return False

    # ─── Animação ──────────────────────────────────────

    def _anim_tick(self):
        self.character.tick()
        self.da.queue_draw()
        return True

    # ─── Sistema unificado de tarefas ─────────────────

    def _use_model_tasks(self):
        return self.cfg.get("accessibility_use_model_defaults", False)

    def _get_model_tasks(self, task_type):
        tasks = getattr(model, "ACCESSIBILITY_TASKS", {}).get(task_type, [])
        return [dict(t, type=task_type) for t in tasks]

    def _manual_task(self, task_type):
        if task_type == "screen" and self.cfg.get("accessibility_enabled", False):
            mode = self.cfg.get("accessibility_mode", "aleatorio")
            return [{
                "type": "screen", "prompt": model.ACCESSIBILITY_SCREEN_PROMPT,
                "mode": mode,
                "min_interval": max(5, self.cfg.get("accessibility_min_interval", 15)),
                "max_interval": max(5, self.cfg.get("accessibility_max_interval", 60)),
                "exact_interval": max(5, self.cfg.get("accessibility_interval", 30)),
            }]
        if task_type == "audio" and self.cfg.get("accessibility_audio_enabled", False):
            mode = self.cfg.get("accessibility_audio_mode", "aleatorio")
            return [{
                "type": "audio", "prompt": model.ACCESSIBILITY_AUDIO_PROMPT,
                "mode": mode,
                "min_interval": max(5, self.cfg.get("accessibility_audio_min_interval", 5)),
                "max_interval": max(5, self.cfg.get("accessibility_audio_max_interval", 30)),
                "exact_interval": max(5, self.cfg.get("accessibility_audio_interval", 10)),
            }]
        if task_type == "speech" and self.cfg.get("accessibility_speech_enabled", False):
            mode = self.cfg.get("speech_mode", "aleatorio")
            return [{
                "type": "speech", "prompt": None,
                "mode": mode,
                "min_interval": max(5, self.cfg.get("speech_min_interval", 30)),
                "max_interval": max(5, self.cfg.get("speech_max_interval", 120)),
                "exact_interval": max(5, self.cfg.get("speech_exact_interval", 60)),
            }]
        return []

    def _get_tasks(self, task_type):
        if self._use_model_tasks():
            return self._get_model_tasks(task_type)
        return self._manual_task(task_type)

    def _task_interval(self, task):
        if task.get("mode") == "exato":
            return task.get("exact_interval", 60)
        lo = task.get("min_interval", 30)
        hi = task.get("max_interval", 120)
        return random.randint(lo, hi)

    def _stop_all_timers(self):
        for tid, _ in self._task_timers:
            GLib.source_remove(tid)
        self._task_timers = []

    def _start_all_timers(self):
        self._stop_all_timers()
        for task_type in ("screen", "audio", "speech"):
            for task in self._get_tasks(task_type):
                self._schedule_task(task)

    def _schedule_task(self, task):
        interval = self._task_interval(task)
        tid = GLib.timeout_add_seconds(interval, self._on_task_tick, task)
        self._task_timers.append((tid, task))
        log("task %s agendada em %ss (%s)", task["type"], interval, task.get("mode", "?"))

    def _on_task_tick(self, task):
        self._stop_task_timers(task)
        if task["type"] == "screen":
            self._do_screen_task(task)
        elif task["type"] == "audio":
            self._do_audio_task(task)
        elif task["type"] == "speech":
            self._do_speech_task(task)
        self._schedule_task(task)
        return False

    def _stop_task_timers(self, task):
        self._task_timers = [(tid, t) for tid, t in self._task_timers if t is not task]

    def _do_screen_task(self, task):
        if self._task_busy["screen"]:
            return
        img = _screenshot_fn()
        if not img or img.startswith("erro") or img.startswith("Não"):
            return
        self._task_busy["screen"] = True
        prompt = task.get("prompt", model.ACCESSIBILITY_SCREEN_PROMPT)
        def on_reply(reply):
            self._task_busy["screen"] = False
            if reply:
                text = self._strip_tool(reply)
                self.show_speech(text, 4)
                self._add_chat_message(text)
        ai.ask(prompt, history=[], callback=on_reply, image_base64=img)

    def _do_audio_task(self, task):
        if self._task_busy["audio"]:
            return
        self._task_busy["audio"] = True
        prompt_template = task.get("prompt", model.ACCESSIBILITY_AUDIO_PROMPT)
        threading.Thread(target=self._capture_and_comment, args=(prompt_template,), daemon=True).start()

    def _capture_and_comment(self, prompt_template):
        def _unbusy():
            self._task_busy["audio"] = False
        try:
            audio_path = _listen_fn()
            if not audio_path or not os.path.exists(audio_path):
                GLib.idle_add(_unbusy)
                return
            transcribed = ai.transcribe(audio_path)
            if not transcribed:
                GLib.idle_add(_unbusy)
                return
            prompt = prompt_template.format(transcribed=transcribed)
            def on_reply(reply):
                self._task_busy["audio"] = False
                if reply:
                    text = self._strip_tool(reply)
                    self.show_speech(text, 4)
                    self._add_chat_message(text)
            ai.ask(prompt, history=[], callback=on_reply)
        except Exception:
            GLib.idle_add(_unbusy)

    def _do_speech_task(self, task):
        phrase = model.phrases.get_fallback("")
        if phrase:
            self.show_speech(phrase, 4)
            self._add_chat_message(phrase)

    def _toggle_use_model_defaults(self, item):
        self.cfg["accessibility_use_model_defaults"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()
        log("tasks: modelo=%s", item.get_active())

    # ─── Wrappers manual mode (chamados pelo menu) ──

    def _toggle_accessibility(self, item):
        self.cfg["accessibility_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()

    def _change_accessibility_mode(self, item, mode):
        if not item.get_active():
            return
        self.cfg["accessibility_mode"] = mode
        config.save(self.cfg)
        self._start_all_timers()

    def _toggle_audio(self, item):
        self.cfg["accessibility_audio_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()

    def _change_audio_mode(self, item, mode):
        if not item.get_active():
            return
        self.cfg["accessibility_audio_mode"] = mode
        config.save(self.cfg)
        self._start_all_timers()

    def _toggle_speech(self, item):
        self.cfg["accessibility_speech_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()

    def _toggle_libras(self, item):
        self.cfg["libras_enabled"] = item.get_active()
        config.save(self.cfg)

    def _change_speech_mode(self, item, mode):
        if not item.get_active():
            return
        self.cfg["speech_mode"] = mode
        config.save(self.cfg)
        self._start_all_timers()

    # ─── One-shot speech timer ───────────────────────

    def _setup_speech_timer(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("speech_timer_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("speech_exact_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("speech_exact_interval", 60), lower=5, upper=600, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["speech_exact_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_speech_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    # ─── Diálogos de configuração manual ─────────────

    def _setup_accessibility_interval(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("accessibility_interval_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("accessibility_interval_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("accessibility_interval", 30), lower=5, upper=300, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_accessibility_min(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("accessibility_min_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("accessibility_min_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("accessibility_min_interval", 15), lower=5, upper=300, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_min_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_accessibility_max(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("accessibility_max_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("accessibility_max_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("accessibility_max_interval", 60), lower=10, upper=300, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_max_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_audio_interval(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("audio_interval_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("audio_interval_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("accessibility_audio_interval", 10), lower=5, upper=120, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_audio_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_audio_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_audio_min(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("audio_min_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("audio_min_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("accessibility_audio_min_interval", 5), lower=5, upper=120, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_audio_min_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_audio_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_audio_max(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("audio_max_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("audio_max_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("accessibility_audio_max_interval", 30), lower=10, upper=120, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["accessibility_audio_max_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_audio_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_speech_min(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("speech_min_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("speech_min_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("speech_min_interval", 30), lower=5, upper=600, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["speech_min_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_speech_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_speech_max(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("speech_max_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("speech_max_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("speech_max_interval", 120), lower=10, upper=600, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["speech_max_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_speech_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    def _setup_speech_exact(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("speech_exact_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 100)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("speech_exact_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(value=self.cfg.get("speech_exact_interval", 60), lower=5, upper=600, step_increment=5)
        spin = Gtk.SpinButton(adjustment=adj); spin.set_numeric(True)
        area.pack_start(spin, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["speech_exact_interval"] = int(spin.get_value())
            config.save(self.cfg)
            if self.cfg.get("accessibility_speech_enabled", False):
                self._start_all_timers()
        dialog.destroy()

    # ─── Alarme ───────────────────────────────────────

    def _start_alarm_check(self):
        self._stop_alarm_check()
        self._alarm_timer_id = GLib.timeout_add_seconds(30, self._alarm_check)
        log("alarme: verificação iniciada (a cada 30s)")

    def _stop_alarm_check(self):
        if self._alarm_timer_id is not None:
            GLib.source_remove(self._alarm_timer_id)
            self._alarm_timer_id = None

    def _alarm_check(self):
        import datetime
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        self._alarm_fired_today = {k for k in self._alarm_fired_today if k[1] == today}
        alarms = self.cfg.get("alarms", [])
        for i, alm in enumerate(alarms):
            if not alm.get("enabled", True):
                continue
            if alm["hour"] == now.hour and alm["minute"] == now.minute:
                key = (i, today)
                if key not in self._alarm_fired_today:
                    self._alarm_fired_today.add(key)
                    log("alarme %d disparado: %02d:%02d", i, alm["hour"], alm["minute"])
                    self._trigger_alarm()
        return True

    def _trigger_alarm(self):
        if self._alarm_ringing:
            return
        self._alarm_ringing = True
        self.character.set_mood(Mood.DANCA)
        phrases = getattr(model.phrases, "ALARM_PHRASES", None)
        if phrases:
            msg = random.choice(phrases)
        else:
            msg = self._("alarm_stopped_generic")
        self.show_speech(msg, 6)
        self._add_chat_message(msg)
        if hasattr(self, '_alarm_stop_item'):
            self._alarm_stop_item.set_sensitive(True)
        threading.Thread(target=self._play_ringtone_loop, daemon=True).start()

    def _play_ringtone_loop(self):
        path = model.RINGTONE_PATH
        if not os.path.exists(path):
            log("ringtone não encontrado: %s", path)
            return
        while self._alarm_ringing:
            self._alarm_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._alarm_process.wait()

    def _stop_alarm(self):
        self._alarm_ringing = False
        if self._alarm_process is not None:
            self._alarm_process.terminate()
            self._alarm_process = None
        if self.character.mood == Mood.DANCA:
            self.character.set_mood(Mood.NORMAL)
        if hasattr(self, '_alarm_stop_item'):
            self._alarm_stop_item.set_sensitive(False)
        phrase = model.phrases.pick("ALARM_STOPPED", self._("alarm_stopped_msg"))
        self.show_speech(phrase, 3)
        self._add_chat_message(phrase)
        self._start_alarm_check()

    def _alarm_stop_from_chat(self, _win_or_text, *args):
        if isinstance(_win_or_text, str):
            text = _win_or_text
        elif args:
            text = args[0]
        else:
            return
        stop_words = {"para", "pare", "parar", "desliga", "desligar", "cala", "calar", "stop", "chega", "silêncio", "silencio"}
        if self._alarm_ringing and any(w in text.lower() for w in stop_words):
            self._stop_alarm()

    def _toggle_alarm_item(self, item, idx):
        alarms = self.cfg.get("alarms", [])
        if 0 <= idx < len(alarms):
            alarms[idx]["enabled"] = item.get_active()
            config.save(self.cfg)

    def _delete_alarm(self, _item, idx):
        alarms = self.cfg.get("alarms", [])
        if 0 <= idx < len(alarms):
            deleted = alarms.pop(idx)
            self.cfg["alarms"] = alarms
            config.save(self.cfg)
            phrase = model.phrases.pick("ALARM_DELETED", self._("alarm_deleted_msg"))
            self.show_speech(f"{phrase} ({deleted['hour']:02d}:{deleted['minute']:02d})", 3)

    def _setup_alarm(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("add_alarm_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_add"), Gtk.ResponseType.OK)
        dialog.set_default_size(300, 240)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(self._("add_alarm_markup"))
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_halign(Gtk.Align.CENTER)
        hbox.set_margin_top(12)

        hour_lbl = Gtk.Label(label=self._("add_alarm_hour_label"))
        hbox.pack_start(hour_lbl, False, False, 2)
        hour_adj = Gtk.Adjustment(value=8, lower=0, upper=23, step_increment=1)
        hour_spin = Gtk.SpinButton(adjustment=hour_adj)
        hour_spin.set_numeric(True); hour_spin.set_wrap(True); hour_spin.set_size_request(60, -1)
        hbox.pack_start(hour_spin, False, False, 2)

        sep = Gtk.Label(label=":")
        hbox.pack_start(sep, False, False, 2)

        min_lbl = Gtk.Label(label=self._("add_alarm_min_label"))
        hbox.pack_start(min_lbl, False, False, 2)
        min_adj = Gtk.Adjustment(value=0, lower=0, upper=59, step_increment=5)
        min_spin = Gtk.SpinButton(adjustment=min_adj)
        min_spin.set_numeric(True); min_spin.set_wrap(True); min_spin.set_size_request(60, -1)
        hbox.pack_start(min_spin, False, False, 2)

        area.pack_start(hbox, False, False, 6)

        name_lbl = Gtk.Label(label=self._("add_alarm_name_label"))
        name_lbl.set_xalign(0)
        area.pack_start(name_lbl, False, False, 2)
        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text(self._("add_alarm_name_placeholder"))
        area.pack_start(name_entry, False, False, 4)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            alarms = self.cfg.get("alarms", [])
            alarms.append({
                "hour": int(hour_spin.get_value()),
                "minute": int(min_spin.get_value()),
                "enabled": True,
                "name": name_entry.get_text().strip(),
            })
            self.cfg["alarms"] = alarms
            config.save(self.cfg)
            self.show_speech(model.phrases.pick("ALARM_ADDED", self._("alarm_added_msg")), 3)
            self._start_alarm_check()
        dialog.destroy()

    # ─── Balão de fala ────────────────────────────────

    def show_speech(self, text, duration=3):
        if self.cfg.get("libras_enabled", False):
            translated = libras.translate(text)
            display = f"[LIBRAS] {translated}" if translated != text else text
        else:
            display = text
        self.speech_queue.append((display, duration))
        if self.talking_timer is None:
            self._show_next_speech()
        self._speak_text(text)

    def _add_chat_message(self, text):
        text = self._strip_tool(text)
        from desktop_pet.chat import _load_history, _save_history
        history = _load_history()
        history.append({"role": "assistant", "content": text})
        _save_history(history)
        if self.chat_window is not None:
            self.chat_window.add_message(text)

    @staticmethod
    def _strip_tool(text):
        import re
        return re.sub(r'(?m)^TOOL:.*$', '', text).strip()

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

    # ─── Desenho e layout ─────────────────────────────

    def _get_layout(self):
        wx, _ = self.get_position()
        screen = self.get_screen()
        sw = screen.get_width()
        alloc = self.da.get_allocation()
        ww = alloc.width if alloc.width > 100 else WIN_W

        scale = self.cfg.get("window_scale", 5)
        cw = 32 * scale

        side = self.cfg.get("bubble_side", config.BUBBLE_AUTO)
        if side == config.BUBBLE_LEFT:
            on_right = False
        elif side == config.BUBBLE_RIGHT:
            on_right = True
        else:
            on_right = (wx + ww // 2) > (sw // 2)

        if on_right:
            char_x = ww - cw - MARGIN
            bubble_x = MARGIN
            tail_dir = 1
        else:
            char_x = MARGIN
            bubble_x = MARGIN + cw + GAP
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

    # ─── Eventos do mouse ─────────────────────────────

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

    # ─── Menu de contexto ─────────────────────────────

    def _show_context_menu(self, ev):
        menu = Gtk.Menu()

        # ── Conversa ────────────────────────────────
        chat_item = Gtk.MenuItem.new_with_label(self._("menu_chat"))
        chat_item.connect("activate", lambda _: self._open_chat())
        menu.append(chat_item)

        # ── Alarme ────────────────────────────────
        alarm_menu = Gtk.Menu()
        alarm_sub = Gtk.MenuItem.new_with_label(self._("menu_alarm"))
        alarm_sub.set_submenu(alarm_menu)

        add_alarm = Gtk.MenuItem.new_with_label(self._("menu_add_alarm"))
        add_alarm.connect("activate", self._setup_alarm)
        alarm_menu.append(add_alarm)

        alarm_menu.append(Gtk.SeparatorMenuItem())

        for i, alm in enumerate(self.cfg.get("alarms", [])):
            label = f"{alm['hour']:02d}:{alm['minute']:02d}"
            if alm.get("name"):
                label += f" - {alm['name']}"
            sub = Gtk.Menu()
            sub_item = Gtk.MenuItem.new_with_label(label)
            sub_item.set_submenu(sub)
            toggle_item = Gtk.CheckMenuItem.new_with_label(self._("alarm_toggle_label"))
            toggle_item.set_active(alm.get("enabled", True))
            toggle_item.connect("toggled", self._toggle_alarm_item, i)
            sub.append(toggle_item)
            delete_item = Gtk.MenuItem.new_with_label(self._("alarm_delete_label"))
            delete_item.connect("activate", self._delete_alarm, i)
            sub.append(delete_item)
            alarm_menu.append(sub_item)

        alarm_menu.append(Gtk.SeparatorMenuItem())

        self._alarm_stop_item = Gtk.MenuItem.new_with_label(self._("menu_stop_alarm"))
        self._alarm_stop_item.connect("activate", lambda _: self._stop_alarm())
        self._alarm_stop_item.set_sensitive(self._alarm_ringing)
        alarm_menu.append(self._alarm_stop_item)

        menu.append(alarm_sub)

        # ── Modelo do pet ──────────────────────────
        model_menu = Gtk.Menu()
        model_sub = Gtk.MenuItem.new_with_label(self._("menu_model"))
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

        menu.append(model_sub)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Configurações ─────────────────────────
        cfg_menu = Gtk.Menu()
        cfg_sub = Gtk.MenuItem.new_with_label(self._("menu_settings"))
        cfg_sub.set_submenu(cfg_menu)

        # ── 🖥  Aparência ──
        appear_menu = Gtk.Menu()
        appear_sub = Gtk.MenuItem.new_with_label(self._("menu_appearance"))
        appear_sub.set_submenu(appear_menu)

        top_item = Gtk.CheckMenuItem.new_with_label(self._("menu_always_on_top"))
        top_item.set_active(self.cfg.get("always_on_top", True))
        top_item.connect("toggled", self._toggle_ontop)
        appear_menu.append(top_item)

        bubble_menu = Gtk.Menu()
        bubble_sub = Gtk.MenuItem.new_with_label(self._("menu_bubble_side"))
        bubble_sub.set_submenu(bubble_menu)
        current_side = self.cfg.get("bubble_side", config.BUBBLE_AUTO)
        group_side = []
        for key, label in [
            (config.BUBBLE_AUTO, self._("menu_bubble_auto")),
            (config.BUBBLE_LEFT, self._("menu_bubble_left")),
            (config.BUBBLE_RIGHT, self._("menu_bubble_right")),
        ]:
            item = Gtk.RadioMenuItem.new_with_label(group_side, label)
            if key == current_side:
                item.set_active(True)
            item.connect("activate", self._change_bubble_side, key)
            bubble_menu.append(item)
            group_side = [item]
        appear_menu.append(bubble_sub)

        appear_menu.append(Gtk.SeparatorMenuItem())

        scale_item = Gtk.MenuItem.new_with_label(self._("menu_window_size"))
        scale_item.connect("activate", self._setup_window_scale)
        appear_menu.append(scale_item)

        cfg_menu.append(appear_sub)

        cfg_menu.append(Gtk.SeparatorMenuItem())

        # ── 🤖  Acessibilidade / Automação ──
        acc_menu = Gtk.Menu()
        acc_sub = Gtk.MenuItem.new_with_label(self._("menu_automation"))
        acc_sub.set_submenu(acc_menu)

        use_model = self._use_model_tasks()

        model_defaults_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_model_defaults"))
        model_defaults_toggle.set_active(use_model)
        model_defaults_toggle.connect("toggled", self._toggle_use_model_defaults)
        acc_menu.append(model_defaults_toggle)

        acc_menu.append(Gtk.SeparatorMenuItem())

        # Leitura de tela
        screen_sub = Gtk.MenuItem.new_with_label(self._("menu_screen_reading"))
        screen_menu = Gtk.Menu()
        screen_sub.set_submenu(screen_menu)

        screen_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_enable"))
        screen_toggle.set_active(self.cfg.get("accessibility_enabled", False))
        screen_toggle.connect("toggled", self._toggle_accessibility)
        screen_toggle.set_sensitive(not use_model)
        screen_menu.append(screen_toggle)

        screen_menu.append(Gtk.SeparatorMenuItem())

        current_screen_mode = self.cfg.get("accessibility_mode", "aleatorio")
        group_screen = []
        for mode, label in [("aleatorio", self._("menu_random")), ("exato", self._("menu_exact"))]:
            item = Gtk.RadioMenuItem.new_with_label(group_screen, label)
            if mode == current_screen_mode:
                item.set_active(True)
            item.connect("activate", self._change_accessibility_mode, mode)
            item.set_sensitive(not use_model)
            screen_menu.append(item)
            group_screen = [item]

        screen_menu.append(Gtk.SeparatorMenuItem())

        if current_screen_mode == "aleatorio":
            screen_min = Gtk.MenuItem.new_with_label(self._("menu_minimum"))
            screen_min.connect("activate", self._setup_accessibility_min)
            screen_min.set_sensitive(not use_model)
            screen_menu.append(screen_min)
            screen_max = Gtk.MenuItem.new_with_label(self._("menu_maximum"))
            screen_max.connect("activate", self._setup_accessibility_max)
            screen_max.set_sensitive(not use_model)
            screen_menu.append(screen_max)
        else:
            screen_interval = Gtk.MenuItem.new_with_label(self._("menu_interval"))
            screen_interval.connect("activate", self._setup_accessibility_interval)
            screen_interval.set_sensitive(not use_model)
            screen_menu.append(screen_interval)

        acc_menu.append(screen_sub)

        # Áudio do desktop
        audio_sub = Gtk.MenuItem.new_with_label(self._("menu_desktop_audio"))
        audio_menu = Gtk.Menu()
        audio_sub.set_submenu(audio_menu)

        audio_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_enable"))
        audio_toggle.set_active(self.cfg.get("accessibility_audio_enabled", False))
        audio_toggle.connect("toggled", self._toggle_audio)
        audio_toggle.set_sensitive(not use_model)
        audio_menu.append(audio_toggle)

        audio_menu.append(Gtk.SeparatorMenuItem())

        current_audio_mode = self.cfg.get("accessibility_audio_mode", "aleatorio")
        group_audio = []
        for mode, label in [("aleatorio", self._("menu_random")), ("exato", self._("menu_exact"))]:
            item = Gtk.RadioMenuItem.new_with_label(group_audio, label)
            if mode == current_audio_mode:
                item.set_active(True)
            item.connect("activate", self._change_audio_mode, mode)
            item.set_sensitive(not use_model)
            audio_menu.append(item)
            group_audio = [item]

        audio_menu.append(Gtk.SeparatorMenuItem())

        if current_audio_mode == "aleatorio":
            audio_min = Gtk.MenuItem.new_with_label(self._("menu_minimum"))
            audio_min.connect("activate", self._setup_audio_min)
            audio_min.set_sensitive(not use_model)
            audio_menu.append(audio_min)
            audio_max = Gtk.MenuItem.new_with_label(self._("menu_maximum"))
            audio_max.connect("activate", self._setup_audio_max)
            audio_max.set_sensitive(not use_model)
            audio_menu.append(audio_max)
        else:
            audio_interval = Gtk.MenuItem.new_with_label(self._("menu_interval"))
            audio_interval.connect("activate", self._setup_audio_interval)
            audio_interval.set_sensitive(not use_model)
            audio_menu.append(audio_interval)

        acc_menu.append(audio_sub)

        # Falas aleatórias
        speech_sub = Gtk.MenuItem.new_with_label(self._("menu_random_speech"))
        speech_menu = Gtk.Menu()
        speech_sub.set_submenu(speech_menu)

        speech_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_enable"))
        speech_toggle.set_active(self.cfg.get("accessibility_speech_enabled", False))
        speech_toggle.connect("toggled", self._toggle_speech)
        speech_toggle.set_sensitive(not use_model)
        speech_menu.append(speech_toggle)

        speech_menu.append(Gtk.SeparatorMenuItem())

        current_speech_mode = self.cfg.get("speech_mode", "aleatorio")
        group_speech = []
        for mode, label in [("aleatorio", self._("menu_random")), ("exato", self._("menu_exact"))]:
            item = Gtk.RadioMenuItem.new_with_label(group_speech, label)
            if mode == current_speech_mode:
                item.set_active(True)
            item.connect("activate", self._change_speech_mode, mode)
            item.set_sensitive(not use_model)
            speech_menu.append(item)
            group_speech = [item]

        speech_menu.append(Gtk.SeparatorMenuItem())

        if current_speech_mode == "aleatorio":
            speech_min = Gtk.MenuItem.new_with_label(self._("menu_minimum"))
            speech_min.connect("activate", self._setup_speech_min)
            speech_min.set_sensitive(not use_model)
            speech_menu.append(speech_min)
            speech_max = Gtk.MenuItem.new_with_label(self._("menu_maximum"))
            speech_max.connect("activate", self._setup_speech_max)
            speech_max.set_sensitive(not use_model)
            speech_menu.append(speech_max)
        else:
            speech_exact = Gtk.MenuItem.new_with_label(self._("menu_interval"))
            speech_exact.connect("activate", self._setup_speech_exact)
            speech_exact.set_sensitive(not use_model)
            speech_menu.append(speech_exact)

        speech_menu.append(Gtk.SeparatorMenuItem())

        speech_timer = Gtk.MenuItem.new_with_label(self._("menu_timer"))
        speech_timer.connect("activate", self._setup_speech_timer)
        speech_timer.set_sensitive(not use_model)
        speech_menu.append(speech_timer)

        acc_menu.append(speech_sub)

        acc_menu.append(Gtk.SeparatorMenuItem())

        libras_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_libras"))
        libras_toggle.set_active(self.cfg.get("libras_enabled", False))
        libras_toggle.connect("toggled", self._toggle_libras)
        acc_menu.append(libras_toggle)

        cfg_menu.append(acc_sub)

        cfg_menu.append(Gtk.SeparatorMenuItem())

        # ── 🎤  Áudio ──
        audio_cfg_menu = Gtk.Menu()
        audio_cfg_sub = Gtk.MenuItem.new_with_label(self._("menu_audio_cfg"))
        audio_cfg_sub.set_submenu(audio_cfg_menu)

        # ── Voz (TTS) ──
        tts_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_tts"))
        tts_toggle.set_active(self.cfg.get("tts_enabled", False))
        tts_toggle.connect("toggled", self._toggle_tts)
        audio_cfg_menu.append(tts_toggle)

        tts_prov_menu = Gtk.Menu()
        tts_prov_sub = Gtk.MenuItem.new_with_label(self._("menu_tts_provider"))
        tts_prov_sub.set_submenu(tts_prov_menu)
        current_tts = self.cfg.get("tts_provider", "auto")
        group_tts = []
        for tts_key, tts_label in [
            ("auto", self._("tts_provider_auto")),
            ("fish_audio", self._("tts_provider_fish") + " (pago)"),
            ("edge_tts", self._("tts_provider_edge")),
            ("pyttsx3", self._("tts_provider_pyttsx")),
        ]:
            item = Gtk.RadioMenuItem.new_with_label(group_tts, tts_label)
            if tts_key == current_tts:
                item.set_active(True)
            item.connect("activate", self._change_tts_provider, tts_key)
            tts_prov_menu.append(item)
            group_tts = [item]
        audio_cfg_menu.append(tts_prov_sub)

        tts_device_item = Gtk.MenuItem.new_with_label(self._("menu_tts_device"))
        tts_device_item.connect("activate", self._setup_tts_device)
        audio_cfg_menu.append(tts_device_item)

        fish_setup_item = Gtk.MenuItem.new_with_label(self._("menu_configure_fish") + " (pago)")
        fish_setup_item.connect("activate", self._setup_fish_audio)
        audio_cfg_menu.append(fish_setup_item)

        audio_cfg_menu.append(Gtk.SeparatorMenuItem())

        # ── Microfone (STT) ──
        mic_toggle = Gtk.CheckMenuItem.new_with_label(self._("menu_mic_stt"))
        mic_toggle.set_active(self.cfg.get("mic_stt_enabled", False))
        mic_toggle.connect("toggled", self._toggle_mic_stt)
        audio_cfg_menu.append(mic_toggle)

        mic_mode_menu = Gtk.Menu()
        mic_mode_sub = Gtk.MenuItem.new_with_label(self._("menu_mic_mode"))
        mic_mode_sub.set_submenu(mic_mode_menu)
        current_stt_mode = self.cfg.get("mic_stt_mode", "toggle")
        group_stt = []
        for val, lbl in [("hold", self._("menu_hold_to_talk")), ("toggle", self._("menu_mic_open"))]:
            item = Gtk.RadioMenuItem.new_with_label(group_stt, lbl)
            if val == current_stt_mode:
                item.set_active(True)
            item.connect("activate", self._change_mic_stt_mode, val)
            mic_mode_menu.append(item)
            group_stt = [item]
        audio_cfg_menu.append(mic_mode_sub)

        mic_device_item = Gtk.MenuItem.new_with_label(self._("menu_mic_device"))
        mic_device_item.connect("activate", self._setup_mic_device)
        audio_cfg_menu.append(mic_device_item)

        # ── Atalhos ──
        shortcuts_menu = Gtk.Menu()
        shortcuts_sub = Gtk.MenuItem.new_with_label(self._("menu_shortcuts"))
        shortcuts_sub.set_submenu(shortcuts_menu)

        shortcut_item = Gtk.MenuItem.new_with_label(self._("menu_mic_shortcut"))
        shortcut_item.connect("activate", self._setup_stt_shortcut)
        shortcuts_menu.append(shortcut_item)

        global_item = Gtk.MenuItem.new_with_label(self._("menu_global_shortcut"))
        global_item.connect("activate", self._show_global_shortcut_help)
        shortcuts_menu.append(global_item)

        audio_cfg_menu.append(shortcuts_sub)

        cfg_menu.append(audio_cfg_sub)

        cfg_menu.append(Gtk.SeparatorMenuItem())

        # ── 🧠  Inteligência ──
        ai_menu = Gtk.Menu()
        ai_sub = Gtk.MenuItem.new_with_label(self._("menu_intelligence"))
        ai_sub.set_submenu(ai_menu)

        provider_menu = Gtk.Menu()
        provider_sub = Gtk.MenuItem.new_with_label(self._("menu_ai_provider"))
        provider_sub.set_submenu(provider_menu)
        current = self.cfg.get("ai_provider", config.PROVIDER_AUTO)
        group_prov = []
        for key, label in [
            (config.PROVIDER_AUTO, self._("menu_provider_auto")),
            (config.PROVIDER_GROQ, self._("menu_provider_groq")),
            (config.PROVIDER_GEMINI, self._("menu_provider_gemini")),
            (config.PROVIDER_HF, self._("menu_provider_hf")),
            (config.PROVIDER_OLLAMA, self._("menu_provider_ollama")),
            (config.PROVIDER_PHRASES, self._("menu_provider_phrases")),
        ]:
            item = Gtk.RadioMenuItem.new_with_label(group_prov, label)
            if key == current:
                item.set_active(True)
            item.connect("activate", self._change_provider, key)
            provider_menu.append(item)
            group_prov = [item]
        ai_menu.append(provider_sub)

        gemini_setup = Gtk.MenuItem.new_with_label(self._("menu_configure_gemini"))
        gemini_setup.connect("activate", lambda _: self._setup_gemini())
        ai_menu.append(gemini_setup)

        groq_setup = Gtk.MenuItem.new_with_label(self._("menu_configure_groq"))
        groq_setup.connect("activate", lambda _: self._setup_groq())
        ai_menu.append(groq_setup)

        hf_setup = Gtk.MenuItem.new_with_label(self._("menu_configure_hf"))
        hf_setup.connect("activate", lambda _: self._setup_hf())
        ai_menu.append(hf_setup)

        ollama_models = self._list_ollama_models()
        if ollama_models:
            ollama_menu = Gtk.Menu()
            ollama_sub = Gtk.MenuItem.new_with_label(self._("menu_ollama_model"))
            ollama_sub.set_submenu(ollama_menu)
            current_om = self.cfg.get("ollama_model", "")
            group_om = []
            for m in ollama_models:
                item = Gtk.RadioMenuItem.new_with_label(group_om, m)
                if m == current_om or (not current_om and group_om == []):
                    item.set_active(True)
                item.connect("activate", self._change_ollama_model, m)
                ollama_menu.append(item)
                group_om = [item]
            ai_menu.append(ollama_sub)

        ai_menu.append(Gtk.SeparatorMenuItem())

        tools_menu = Gtk.Menu()
        tools_sub = Gtk.MenuItem.new_with_label(self._("menu_permissions"))
        tools_sub.set_submenu(tools_menu)
        for key, label in [
            ("tool_read_file", self._("menu_perm_read_file")),
            ("tool_list_files", self._("menu_perm_list_files")),
            ("tool_run_command", self._("menu_perm_run_command")),
            ("tool_write_file", self._("menu_perm_write_file")),
            ("tool_screenshot", self._("menu_perm_screenshot")),
            ("tool_open_url", self._("menu_perm_open_url")),
            ("tool_listen", self._("menu_perm_listen")),
        ]:
            item = Gtk.CheckMenuItem.new_with_label(label)
            item.set_active(self.cfg.get(key, False))
            item.connect("toggled", self._toggle_tool, key)
            tools_menu.append(item)
        ai_menu.append(tools_sub)

        cfg_menu.append(ai_sub)

        cfg_menu.append(Gtk.SeparatorMenuItem())

        # ── 🌐  Idioma ──
        lang_menu = Gtk.Menu()
        lang_sub = Gtk.MenuItem.new_with_label(self._("menu_language"))
        lang_sub.set_submenu(lang_menu)
        current_lang = self.cfg.get("language", "pt")
        group_lang = []
        for lang_code, lang_label in [("pt", "Português"), ("en", "English"), ("jp", "日本語")]:
            item = Gtk.RadioMenuItem.new_with_label(group_lang, lang_label)
            if lang_code == current_lang:
                item.set_active(True)
            item.connect("activate", self._change_language, lang_code)
            lang_menu.append(item)
            group_lang = [item]
        cfg_menu.append(lang_sub)

        cfg_menu.append(Gtk.SeparatorMenuItem())

        # ── 👤  Conta ──
        profile_item = Gtk.MenuItem.new_with_label(self._("menu_profile"))
        profile_item.connect("activate", lambda _: self._setup_profile())
        cfg_menu.append(profile_item)

        about_item = Gtk.MenuItem.new_with_label(self._("menu_about"))
        about_item.connect("activate", self._show_about)
        cfg_menu.append(about_item)

        menu.append(cfg_sub)

        # ── Limpar Histórico ────────────────────────
        clear_item = Gtk.MenuItem.new_with_label(self._("menu_clear_history"))
        clear_item.connect("activate", self._clear_history)
        menu.append(clear_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Sair ───────────────────────────────────
        quit_item = Gtk.MenuItem.new_with_label(self._("menu_quit"))
        quit_item.connect("activate", lambda _: self._on_destroy())
        menu.append(quit_item)

        menu.show_all()
        menu.popup_at_pointer(ev)

    # ─── Janela de chat ───────────────────────────────

    def _open_chat(self):
        if self.chat_window is not None:
            self.chat_window.present()
            return
        self.chat_window = ChatWindow(self)
        self.chat_window.connect("destroy", self._on_chat_closed)

        self.chat_window.connect("teto-speech", self._on_chat_speech)
        self.chat_window.connect("alarm-command", self._alarm_stop_from_chat)
        self.chat_window.connect("key-press-event", self._on_key_press)
        self.chat_window.connect("key-release-event", self._on_key_release)
        self.chat_window.entry.connect("key-press-event", self._on_key_press)
        self.chat_window.entry.connect("key-release-event", self._on_key_release)
        self.chat_window.show_all()

    def _on_chat_speech(self, _win, text, mood):
        if not self._alarm_ringing:
            if mood:
                self.character.set_mood(mood)
        self.show_speech(self._strip_tool(text))
        self._alarm_stop_from_chat(_win, text, mood)

    def _speak_text(self, text):
        if not self.cfg.get("tts_enabled", False):
            return
        voice_config = dict(getattr(model, "TTS_VOICE", {}))
        if not voice_config:
            return
        fish_voice = self.cfg.get("fish_audio_voice", "")
        if fish_voice:
            voice_config["fish_audio"] = fish_voice
        provider = self.cfg.get("tts_provider", "auto")
        api_key = self.cfg.get("fish_audio_key", "") or None
        device = self.cfg.get("tts_device", "") or None
        threading.Thread(
            target=tts_mod.speak,
            args=(text, provider, voice_config, api_key, device),
            daemon=True,
        ).start()

    def _on_chat_closed(self, _w=None):
        self.chat_window = None

    def _clear_history(self, _item=None):
        if self.chat_window is not None:
            self.chat_window.clear_history()
        else:
            try:
                path = os.path.expanduser(f"~/.config/teto-pet/history/{model.MODEL_ID}.json")
                os.remove(path)
            except OSError:
                pass
        self.show_speech(self._("history_cleared"), 3)

    # ─── Configurações diversas ───────────────────────

    def _toggle_ontop(self, item):
        self.cfg["always_on_top"] = item.get_active()
        self.set_keep_above(item.get_active())
        config.save(self.cfg)

    def _toggle_tool(self, item, key):
        self.cfg[key] = item.get_active()
        config.save(self.cfg)

    def _toggle_mic_stt(self, item):
        self.cfg["mic_stt_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_mic_listener()

    def _toggle_tts(self, item):
        self.cfg["tts_enabled"] = item.get_active()
        config.save(self.cfg)

    def _change_tts_provider(self, item, provider):
        if not item.get_active():
            return
        self.cfg["tts_provider"] = provider
        config.save(self.cfg)

    def _setup_tts_device(self, _item=None):
        devices = tts_mod.list_audio_devices()
        if not devices:
            self.show_speech(self._("no_tts_device"), 3)
            return
        current = self.cfg.get("tts_device", "")
        dialog = Gtk.Dialog(
            title=self._("tts_device_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(400, 250)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("tts_device_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        store = Gtk.ListStore(str, str)
        combo = Gtk.ComboBox.new_with_model(store)
        renderer = Gtk.CellRendererText()
        combo.pack_start(renderer, True)
        combo.add_attribute(renderer, "text", 1)
        idx = 0
        for i, d in enumerate(devices):
            store.append([d["id"], d["description"]])
            if d["id"] == current:
                idx = i
        combo.set_active(idx)
        area.pack_start(combo, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            active_iter = combo.get_active_iter()
            if active_iter is not None:
                device_id = store[active_iter][0]
                self.cfg["tts_device"] = device_id
                config.save(self.cfg)
        dialog.destroy()

    def _setup_fish_audio(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("fish_setup_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_save"), Gtk.ResponseType.OK)
        dialog.set_default_size(420, 240)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(
            "<b>Fish Audio</b>\n\n"
            "Vozes de IA realistas para seu pet.\n\n"
            "1. Crie uma conta em <a href=\"https://fish.audio/app/api-keys\">fish.audio</a>\n"
            "2. Vá em <b>API Keys</b> e crie uma chave\n"
            "3. Copie a chave e cole abaixo\n\n"
            "Voice ID (opcional): Se o modelo tiver uma\n"
            "voz definida em model.py, ela aparece aqui.\n"
            "Deixe vazio para usar a voz padrão."
        )
        lbl.set_line_wrap(True); lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        key_entry = Gtk.Entry()
        key_entry.set_placeholder_text(self._("fish_key_placeholder"))
        key_entry.set_text(self.cfg.get("fish_audio_key", ""))
        key_entry.set_visibility(False)
        area.pack_start(key_entry, False, False, 6)

        current_voice = self.cfg.get("fish_audio_voice", "")
        model_voice = getattr(model, "TTS_VOICE", {}).get("fish_audio", "")
        voice_entry = Gtk.Entry()
        placeholder = model_voice or self._("fish_voice_placeholder")
        voice_entry.set_placeholder_text(placeholder)
        voice_entry.set_text(current_voice)
        area.pack_start(voice_entry, False, False, 6)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://fish.audio/app/api-keys",
            "Abrir página de API Keys",
        )
        area.pack_start(link_btn, False, False, 6)

        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            key = key_entry.get_text().strip()
            voice = voice_entry.get_text().strip()
            if key:
                self.cfg["fish_audio_key"] = key
                self.cfg["fish_audio_voice"] = voice
                config.save(self.cfg)
                self.show_speech(self._("fish_configured"))
            else:
                self.show_speech(self._("fish_no_key"))
        dialog.destroy()

    def _change_mic_stt_mode(self, item, mode):
        if item.get_active():
            self.cfg["mic_stt_mode"] = mode
            config.save(self.cfg)
            self._start_mic_listener()

    def _start_mic_listener(self):
        self._stop_mic_listener()
        if not self.cfg.get("mic_stt_enabled") or self.cfg.get("mic_stt_mode") != "toggle":
            return
        self._mic_listener_timer = GLib.timeout_add_seconds(8, self._mic_listen_tick)
        log("STT: listener contínuo iniciado")

    def _stop_mic_listener(self):
        if self._mic_listener_timer is not None:
            GLib.source_remove(self._mic_listener_timer)
            self._mic_listener_timer = None
        self._mic_listening = False

    def _mic_listen_tick(self):
        if self._mic_listening:
            return True
        if not self.cfg.get("mic_stt_enabled") or self.cfg.get("mic_stt_mode") != "toggle":
            self._stop_mic_listener()
            return False
        self._mic_listening = True
        device = self.cfg.get("mic_stt_device", "") or None
        threading.Thread(target=self._mic_listen_and_respond, args=(device,), daemon=True).start()
        return True

    def _mic_listen_and_respond(self, device):
        try:
            wav = listen_mic(device=device, duration=5)
            if isinstance(wav, str) and wav.startswith("Erro"):
                log("STT contínuo: erro na captura: %s", wav)
                return
            if not wav:
                return
            text = ai.transcribe(wav)
            if text and re.search(r'[a-zA-Záéíóúâêîôûãõçàèìòùäëïöüñ]', text):
                text = text.strip()
                # Ignora transcrições muito curtas (geralmente ruído/alucinação)
                words = text.split()
                if len(words) < 2:
                    log("STT contínuo: ignorado (poucas palavras): %s", text)
                    return
                # Ignora texto repetido (alucinação do Whisper com ruído)
                if text == getattr(self, '_last_stt_text', ''):
                    log("STT contínuo: ignorado (repetido): %s", text)
                    return
                self._last_stt_text = text
                log("STT contínuo: %s", text)
                GLib.idle_add(self._handle_mic_speech, text)
        finally:
            self._mic_listening = False

    def _handle_mic_speech(self, text):
        if self.chat_window is None:
            self._open_chat(hidden=True)
        self.chat_window._process_user_text(text)

    def _open_chat(self, hidden=False):
        if self.chat_window is not None:
            if not hidden:
                self.chat_window.present()
            return
        self.chat_window = ChatWindow(self)
        self.chat_window.connect("destroy", self._on_chat_closed)

        self.chat_window.connect("teto-speech", self._on_chat_speech)
        self.chat_window.connect("alarm-command", self._alarm_stop_from_chat)
        self.chat_window.connect("key-press-event", self._on_key_press)
        self.chat_window.connect("key-release-event", self._on_key_release)
        self.chat_window.entry.connect("key-press-event", self._on_key_press)
        self.chat_window.entry.connect("key-release-event", self._on_key_release)
        self.chat_window.show_all()
        if hidden:
            self.chat_window.hide()

    # ─── Atalho global (Win+V) ────────────────────────

    def _start_ptt_socket_server(self):
        try:
            if os.path.exists(self._ptt_socket_path):
                os.unlink(self._ptt_socket_path)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(self._ptt_socket_path)
            sock.listen(5)
            sock.settimeout(0.1)
            self._create_ptt_helper()
            threading.Thread(target=self._ptt_socket_loop, args=(sock,), daemon=True).start()
        except Exception as e:
            log("PTT socket: %s", e)

    def _create_ptt_helper(self):
        if os.path.exists(self._ptt_helper_path):
            return
        sock_path = self._ptt_socket_path
        helper = f"""#!/bin/bash
# Mate Helper PTT - chamado pelo atalho global
CMD="${{1:-toggle}}"
echo "$CMD" | socat - UNIX-CONNECT:"{sock_path}" 2>/dev/null || \\
  python3 -c "
import socket as s, sys
c = s.socket(s.AF_UNIX, s.SOCK_STREAM)
c.connect('{sock_path}')
c.send((sys.argv[1] if len(sys.argv) > 1 else 'toggle').encode())
c.close()
" "$CMD"
"""
        try:
            os.makedirs(os.path.dirname(self._ptt_helper_path), exist_ok=True)
            with open(self._ptt_helper_path, "w") as f:
                f.write(helper)
            os.chmod(self._ptt_helper_path, 0o755)
        except Exception as e:
            log("PTT helper: %s", e)

    def _ptt_socket_loop(self, sock):
        while True:
            try:
                conn, _addr = sock.accept()
                data = conn.recv(1024)
                conn.close()
                cmd = data.decode().strip()
                if cmd == "press":
                    GLib.idle_add(self._on_global_shortcut_press)
                elif cmd == "release":
                    GLib.idle_add(self._on_global_shortcut_release)
                elif cmd == "toggle":
                    if self._global_recording or self._stt_shortcut_stop_event is not None:
                        GLib.idle_add(self._on_global_shortcut_release)
                    else:
                        GLib.idle_add(self._on_global_shortcut_press)
            except socket.timeout:
                continue
            except Exception as e:
                log("PTT socket loop: %s", e)
                break

    def _setup_global_hotkey(self):
        if not HAS_PYNPUT:
            return
        if self._global_hotkey_listener is not None:
            return

        def on_press(key):
            self._global_keys_state.add(key)
            super_v_pressed = (
                (keyboard.Key.cmd_l in self._global_keys_state or keyboard.Key.cmd_r in self._global_keys_state)
                and hasattr(key, "char") and key.char is not None and key.char.lower() == "v"
            )
            if super_v_pressed:
                self._global_keys_state.discard(key)
                GLib.idle_add(self._on_global_shortcut_press)

        def on_release(key):
            was_win_released = (
                key in (keyboard.Key.cmd_l, keyboard.Key.cmd_r)
                and self._global_recording
            )
            was_v_released = (
                hasattr(key, "char") and key.char is not None and key.char.lower() == "v"
                and keyboard.Key.cmd_l not in self._global_keys_state
                and keyboard.Key.cmd_r not in self._global_keys_state
                and self._global_recording
            )
            self._global_keys_state.discard(key)
            if was_win_released or was_v_released:
                GLib.idle_add(self._on_global_shortcut_release)

        self._global_hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._global_hotkey_listener.daemon = True
        self._global_hotkey_listener.start()

    def _on_global_shortcut_press(self):
        if not self.cfg.get("mic_stt_enabled", False):
            return
        if self.cfg.get("mic_stt_mode") != "hold":
            return
        if self._stt_shortcut_stop_event is not None:
            return
        self._global_recording = True
        self._stt_shortcut_stop_event = threading.Event()
        device = self.cfg.get("mic_stt_device", "") or None
        threading.Thread(
            target=self._mic_shortcut_record, args=(device,),
            daemon=True,
        ).start()

    def _on_global_shortcut_release(self):
        if not self._global_recording:
            return
        self._global_recording = False
        if self._stt_shortcut_stop_event is not None:
            self._stt_shortcut_stop_event.set()

    # ─── Teclado (atalho STT) ────────────────────────

    def _on_key_press(self, _win, event):
        if event.state & Gdk.ModifierType.SUPER_MASK:
            return False
        key = Gdk.keyval_name(event.keyval)
        expected = self.cfg.get("stt_shortcut", "V")
        if key != expected or self._stt_shortcut_stop_event is not None:
            return False
        if not self.cfg.get("mic_stt_enabled", False):
            return False
        if self.cfg.get("mic_stt_mode") != "hold":
            return False
        self._stt_shortcut_stop_event = threading.Event()
        device = self.cfg.get("mic_stt_device", "") or None
        threading.Thread(
            target=self._mic_shortcut_record, args=(device,),
            daemon=True,
        ).start()
        return True

    def _on_key_release(self, _win, event):
        key = Gdk.keyval_name(event.keyval)
        expected = self.cfg.get("stt_shortcut", "V")
        if key == expected and self._stt_shortcut_stop_event is not None:
            log("STT atalho: tecla solta, parando gravação")
            self._stt_shortcut_stop_event.set()
        return True

    def _mic_shortcut_record(self, device):
        try:
            wav = listen_mic(device=device, duration=30, stop_event=self._stt_shortcut_stop_event)
            if isinstance(wav, str) and wav.startswith("Erro"):
                log("STT atalho: erro na captura: %s", wav)
                return
            if not wav:
                return
            text = ai.transcribe(wav)
            if text and re.search(r'[a-zA-Záéíóúâêîôûãõçàèìòùäëïöüñ]', text):
                log("STT atalho: %s", text)
                GLib.idle_add(self._handle_mic_speech, text.strip())
        finally:
            self._stt_shortcut_stop_event = None

    def _show_global_shortcut_help(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("global_shortcut_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(480, 300)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label()
        lbl.set_markup(self._("global_shortcut_markup", path=self._ptt_helper_path))
        lbl.set_line_wrap(True); lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)
        area.show_all()
        dialog.run()
        dialog.destroy()

    def _setup_stt_shortcut(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("stt_shortcut_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(320, 150)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label()
        current = self.cfg.get("stt_shortcut", "V")
        lbl.set_markup(self._("stt_shortcut_markup", current=current))
        lbl.set_line_wrap(True); lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)
        entry = Gtk.Entry()
        entry.set_text(current)
        entry.set_max_length(1)
        entry.set_width_chars(5)
        entry.set_placeholder_text(self._("stt_shortcut_placeholder"))
        entry.connect("key-press-event", lambda w, e: (
            w.set_text(Gdk.keyval_name(e.keyval).upper()),
            True,
        ))
        area.pack_start(entry, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            val = entry.get_text().strip().upper() or "V"
            self.cfg["stt_shortcut"] = val
            config.save(self.cfg)
        dialog.destroy()

    # ─── Tamanho da janela ───────────────────────────

    def _setup_window_scale(self, _item=None):
        dialog = Gtk.Dialog(
            title=self._("window_scale_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(350, 150)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("window_scale_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        adj = Gtk.Adjustment(
            value=self.cfg.get("window_scale", 5),
            lower=3, upper=10, step_increment=1,
        )
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(0)
        scale.set_hexpand(True)
        scale.set_value_pos(Gtk.PositionType.BOTTOM)
        scale.add_mark(5, Gtk.PositionType.BOTTOM, self._("window_scale_default_mark"))
        area.pack_start(scale, False, False, 6)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            val = int(adj.get_value())
            self.cfg["window_scale"] = val
            config.save(self.cfg)
            self._apply_window_scale(val)
        dialog.destroy()

    def _apply_window_scale(self, scale):
        cw = 32 * scale
        ww = MARGIN + cw + GAP + BUBBLE_MAX + MARGIN
        wh = 32 * scale + 50
        self.resize(ww, wh)
        self.da.queue_draw()
        if self.chat_window is not None:
            cw_ratio = scale / 5.0
            cw_w = max(260, int(360 * cw_ratio))
            cw_h = max(300, int(420 * cw_ratio))
            self.chat_window.resize(cw_w, cw_h)

    def _setup_mic_device(self, _item=None):
        mics = list_mic_sources()
        if not mics:
            self.show_speech(self._("no_mic_found"), 3)
            return
        current = self.cfg.get("mic_stt_device", "")
        dialog = Gtk.Dialog(
            title=self._("mic_device_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(350, 200)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("mic_device_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)
        store = Gtk.ListStore(str)
        combo = Gtk.ComboBox.new_with_model(store)
        renderer = Gtk.CellRendererText()
        combo.pack_start(renderer, True)
        combo.add_attribute(renderer, "text", 0)
        idx = 0
        for i, m in enumerate(mics):
            store.append([m])
            if m == current:
                idx = i
        combo.set_active(idx)
        area.pack_start(combo, False, False, 4)
        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            active_iter = combo.get_active_iter()
            if active_iter is not None:
                device = store[active_iter][0]
                self.cfg["mic_stt_device"] = device
                self.cfg["mic_stt_enabled"] = True
                config.save(self.cfg)
                self.show_speech(self._("mic_configured"), 3)
        dialog.destroy()

    def _change_bubble_side(self, item, side):
        if item.get_active():
            self.cfg["bubble_side"] = side
            config.save(self.cfg)
            self.da.queue_draw()

    def _change_language(self, item, lang_code):
        if not item.get_active():
            return
        self.cfg["language"] = lang_code
        config.save(self.cfg)
        self.show_speech("OK! ^_^")
        GLib.timeout_add(1500, self._restart)

    def _change_model(self, item, model_name):
        if not item.get_active():
            return
        self.cfg["active_model"] = model_name
        config.save(self.cfg)
        self.show_speech(self._("restarting_model", model=model_name.replace("_", " ").title()))
        GLib.timeout_add(1500, self._restart)

    def _restart(self):
        x, y = self.get_position()
        self.cfg["window_x"] = x
        self.cfg["window_y"] = y
        config.save(self.cfg)
        subprocess.Popen([sys.executable] + sys.argv)
        Gtk.main_quit()
        return False

    # ─── Diálogos de configuração ─────────────────────

    def _setup_gemini(self):
        dialog = Gtk.Dialog(
            title=self._("gemini_setup_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_save"), Gtk.ResponseType.OK)
        dialog.set_default_size(400, 200)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(self._("gemini_markup"))
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        entry = Gtk.Entry()
        entry.set_placeholder_text(self._("gemini_entry_placeholder"))
        entry.set_text(self.cfg.get("gemini_key", ""))
        entry.set_visibility(False)
        area.pack_start(entry, False, False, 6)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://aistudio.google.com/apikey",
            self._("gemini_link_label"),
        )
        area.pack_start(link_btn, False, False, 6)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            key = entry.get_text().strip()
            if key:
                self.cfg["gemini_key"] = key
                config.save(self.cfg)
                self.show_speech(self._("gemini_configured"))
            else:
                self.show_speech(self._("gemini_no_key"))
        dialog.destroy()

    def _setup_groq(self):
        dialog = Gtk.Dialog(
            title=self._("groq_setup_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_save"), Gtk.ResponseType.OK)
        dialog.set_default_size(400, 220)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(self._("groq_markup"))
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        entry = Gtk.Entry()
        entry.set_placeholder_text(self._("groq_entry_placeholder"))
        entry.set_text(self.cfg.get("groq_key", ""))
        entry.set_visibility(False)
        area.pack_start(entry, False, False, 6)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://console.groq.com/keys",
            self._("groq_link_label"),
        )
        area.pack_start(link_btn, False, False, 6)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            key = entry.get_text().strip()
            if key:
                self.cfg["groq_key"] = key
                config.save(self.cfg)
                self.show_speech(self._("groq_configured"))
            else:
                self.show_speech(self._("groq_no_key"))
        dialog.destroy()

    def _setup_hf(self):
        dialog = Gtk.Dialog(
            title=self._("hf_setup_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_save"), Gtk.ResponseType.OK)
        dialog.set_default_size(400, 220)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(self._("hf_markup"))
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        entry = Gtk.Entry()
        entry.set_placeholder_text(self._("hf_entry_placeholder"))
        entry.set_text(self.cfg.get("hf_token", ""))
        entry.set_visibility(False)
        area.pack_start(entry, False, False, 6)

        link_btn = Gtk.LinkButton.new_with_label(
            "https://huggingface.co/settings/tokens",
            self._("hf_link_label"),
        )
        area.pack_start(link_btn, False, False, 6)

        area.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            token = entry.get_text().strip()
            if token:
                self.cfg["hf_token"] = token
                config.save(self.cfg)
                self.show_speech(self._("hf_configured"))
            else:
                self.show_speech(self._("hf_no_token"))
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
            title=self._("profile_title"),
            transient_for=self,
            flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_save"), Gtk.ResponseType.OK)
        dialog.set_default_size(360, 260)

        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        lbl = Gtk.Label()
        lbl.set_markup(self._("profile_markup"))
        lbl.set_line_wrap(True)
        lbl.set_xalign(0)
        area.pack_start(lbl, False, False, 6)

        name_lbl = Gtk.Label(label=self._("profile_name_label"))
        name_lbl.set_xalign(0)
        area.pack_start(name_lbl, False, False, 2)

        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text(self._("profile_name_placeholder"))
        name_entry.set_text(self.cfg.get("user_name", ""))
        area.pack_start(name_entry, False, False, 4)

        bio_lbl = Gtk.Label(label=self._("profile_bio_label"))
        bio_lbl.set_xalign(0)
        area.pack_start(bio_lbl, False, False, 2)

        bio_entry = Gtk.Entry()
        bio_entry.set_placeholder_text(self._("profile_bio_placeholder"))
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
                self.show_speech(self._("profile_saved_name", name=name))
            else:
                self.show_speech(self._("profile_saved"))
        dialog.destroy()

    def _show_about(self, _item=None):
        about = Gtk.AboutDialog()
        about.set_program_name("Mate Helper")
        about.set_version("0.1.0")
        about.set_comments(self._("about_comments"))
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
        self._stop_all_timers()
        self._stop_mic_listener()
        if self._stt_shortcut_stop_event is not None:
            self._stt_shortcut_stop_event.set()
        if self._global_hotkey_listener is not None:
            self._global_hotkey_listener.stop()
            self._global_hotkey_listener = None
        try:
            if os.path.exists(self._ptt_socket_path):
                os.unlink(self._ptt_socket_path)
        except Exception:
            pass
        self._stop_alarm_check()
        self._stop_alarm()
        subprocess.run(["pkill", "-f", r"parec .*--rate=16000"], capture_output=True)
        ollama_stop()
        Gtk.main_quit()
