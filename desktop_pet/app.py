"""
Mate Helper — Desktop Pet Application

TetoPet is the main GTK.Window subclass that serves as the application's
primary entry point and orchestrator.  It is responsible for:

  * Character animation (Teto sprite sheet with mood-driven frames).
  * Speech bubble rendering (rounded rectangle with directional tail).
  * Chat window for text-based AI conversation.
  * Text-to-Speech (TTS) using multiple providers (system, fish, etc.).
  * Speech-to-Text (STT) via microphone (continuous toggle or push-to-talk).
  * Accessibility task timers (periodic screen description, audio monitoring,
    and random speech).
  * Alarm system (one-shot alarms with ringtone via ffplay).
  * Drag-to-move and double-click-to-open-chat mouse interactions.
  * Wallpaper / full-screen overlay mode.
  * Right-click context menu (alarms, model switching, settings, quit).
  * Full settings window for all configuration options.
  * Global hotkey (Win+V) through a UNIX socket helper binary.
  * In-app keyboard shortcut for STT recording.
  * Persistence of window position and all configuration via config module.
"""

import math
import os
import random
import re
import socket
import subprocess
import sys
import threading
import time

import requests

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

import gi
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo, cairo

from desktop_pet import config, ai
from desktop_pet.log import log
from desktop_pet.models import model

from desktop_pet.character import Teto, Mood, FRAME_MS
from desktop_pet.chat import ChatWindow
from desktop_pet.ai import ollama_ensure_running, ollama_stop
from desktop_pet.tools import screenshot as _screenshot_fn, listen as _listen_fn, listen_mic, list_mic_sources
from desktop_pet import tts as tts_mod
from desktop_pet.settings_window import SettingsWindow


# ─── Constants ──────────────────────────────────────

CHAR_SCALE = 6
CHAR_Y = 20
BUBBLE_W = 190
BUBBLE_PAD = 12
GAP = 16
MARGIN = 16
CHAR_W = 32 * CHAR_SCALE
BUBBLE_MAX = BUBBLE_W + BUBBLE_PAD * 2
WIN_W = MARGIN + CHAR_W + GAP + BUBBLE_MAX + MARGIN
WIN_H = 32 * CHAR_SCALE + 50


# ─── Main Window Class ──────────────────────────────


class TetoPet(Gtk.Window):

    def __init__(self):
        """Initialise the main pet window, load config, set up character, timers,
        drawing area, mouse/ keyboard signals, and show the initial greeting."""
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
        self._last_tts_time = 0
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
        self._bg_surface = None
        self._settings_window = None
        self._ai_sensitive_items = []
        self._ai_backup = None
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

        self._load_background()
        GLib.idle_add(self._apply_wallpaper_if_enabled)
        self.da.connect("button-press-event", self._on_button_press)
        self.da.connect("button-release-event", self._on_button_release)
        self.da.connect("motion-notify-event", self._on_motion)
        self.add(self.da)

        self.connect("destroy", self._on_destroy)
        self.connect("key-press-event", self._on_key_press)
        self.connect("key-release-event", self._on_key_release)

        self.show_all()
        GLib.timeout_add(FRAME_MS, self._anim_tick)

        if self.cfg.get("ai_enabled", True):
            provider = self.cfg.get("ai_provider", config.PROVIDER_AUTO)
            if provider in (config.PROVIDER_AUTO, config.PROVIDER_OLLAMA):
                GLib.idle_add(self._start_ollama_if_needed)

        GLib.idle_add(lambda: self.show_speech(model.phrases.pick("GREETING", self._("greeting")), 5))
        GLib.idle_add(self._setup_global_hotkey)

    def _(self, key, **kwargs):
        """Shortcut for translated strings using the current language from config."""
        return model.get_string(self.cfg.get("language", "pt"), key, **kwargs)

    def _start_ollama_if_needed(self):
        """Ensure Ollama is running; show a speech bubble with the result."""
        if ollama_ensure_running():
            self.show_speech(model.phrases.pick("OLLAMA_STARTED", self._("ollama_started")))
        else:
            self.show_speech(model.phrases.pick("OLLAMA_NOT_FOUND", self._("ollama_not_found")))
        return False

    # ─── Animation ──────────────────────────────────────

    def _anim_tick(self):
        """Advance the character animation one frame and schedule a redraw."""
        self.character.tick()
        self.da.queue_draw()
        return True

    # ─── Task System (Accessibility/Screen/Audio/Speech) ──

    def _use_model_tasks(self):
        """Whether accessibility tasks should use model-defined defaults."""
        return self.cfg.get("accessibility_use_model_defaults", False)

    def _get_model_tasks(self, task_type):
        """Return the list of model-defined tasks for *task_type* ("screen", "audio", "speech")."""
        tasks = getattr(model, "ACCESSIBILITY_TASKS", {}).get(task_type, [])
        return [dict(t, type=task_type) for t in tasks]

    def _manual_task(self, task_type):
        """Build a single task dict from the user's manual config for *task_type*,
        or return an empty list if that type is disabled."""
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
        """Return the list of active tasks for *task_type* (model or manual)."""
        if self._use_model_tasks():
            return self._get_model_tasks(task_type)
        return self._manual_task(task_type)

    def _task_interval(self, task):
        """Compute the scheduling interval for a task in seconds.
        Exact mode uses the configured exact interval; random mode picks
        a value between min_interval and max_interval."""
        if task.get("mode") == "exato":
            return task.get("exact_interval", 60)
        lo = task.get("min_interval", 30)
        hi = task.get("max_interval", 120)
        return random.randint(lo, hi)

    def _stop_all_timers(self):
        """Remove all active GLib task timers."""
        for tid, _ in self._task_timers:
            GLib.source_remove(tid)
        self._task_timers = []

    def _start_all_timers(self):
        """Stop all timers, rebuild the task list from config, and schedule every task."""
        self._stop_all_timers()
        for task_type in ("screen", "audio", "speech"):
            for task in self._get_tasks(task_type):
                self._schedule_task(task)

    def _schedule_task(self, task):
        """Register a one-shot GLib timer for *task* and store its id."""
        interval = self._task_interval(task)
        tid = GLib.timeout_add_seconds(interval, self._on_task_tick, task)
        self._task_timers.append((tid, task))
        log("task %s agendada em %ss (%s)", task["type"], interval, task.get("mode", "?"))

    def _on_task_tick(self, task):
        """Timer callback: stop tracking the task, execute it, then reschedule."""
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
        """Remove *task* from the timer list without cancelling the running timer."""
        self._task_timers = [(tid, t) for tid, t in self._task_timers if t is not task]

    def _do_screen_task(self, task):
        """Take a screenshot, ask AI for a description, and show the result in a speech bubble."""
        if self._task_busy["screen"]:
            return
        if not self.cfg.get("ai_enabled", True):
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
        """Record a short audio clip, transcribe it, send to AI, and show the comment."""
        if self._task_busy["audio"]:
            return
        if not self.cfg.get("ai_enabled", True):
            return
        self._task_busy["audio"] = True
        prompt_template = task.get("prompt", model.ACCESSIBILITY_AUDIO_PROMPT)
        threading.Thread(target=self._capture_and_comment, args=(prompt_template,), daemon=True).start()

    def _capture_and_comment(self, prompt_template):
        """Thread target: capture audio, transcribe via STT, ask AI, show response."""

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
        """Say a random phrase from the model's phrase list."""
        phrase = model.phrases.get_fallback("")
        if phrase:
            self.show_speech(phrase, 4)
            self._add_chat_message(phrase)

    def _toggle_use_model_defaults(self, item):
        """Toggle whether accessibility tasks use the model's built-in defaults."""
        self.cfg["accessibility_use_model_defaults"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()
        log("tasks: modelo=%s", item.get_active())

    # ─── Task Toggle Helpers (called from context menu) ──

    def _toggle_accessibility(self, item):
        """Enable/disable the periodic screen description task."""
        self.cfg["accessibility_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()

    def _change_accessibility_mode(self, item=None, mode=None):
        """Change the scheduling mode for screen tasks (aleatorio/exato)."""
        if item is not None and not item.get_active():
            return
        if mode is None:
            return
        self.cfg["accessibility_mode"] = mode
        config.save(self.cfg)
        self._start_all_timers()

    def _change_audio_mode(self, item=None, mode=None):
        """Change the scheduling mode for audio monitoring tasks."""
        if item is not None and not item.get_active():
            return
        if mode is None:
            return
        self.cfg["accessibility_audio_mode"] = mode
        config.save(self.cfg)
        self._start_all_timers()

    def _change_speech_mode(self, item=None, mode=None):
        """Change the scheduling mode for random speech tasks."""
        if item is not None and not item.get_active():
            return
        if mode is None:
            return
        self.cfg["speech_mode"] = mode
        config.save(self.cfg)
        self._start_all_timers()

    def _toggle_audio(self, item):
        """Enable/disable the periodic audio monitoring task."""
        self.cfg["accessibility_audio_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()

    def _toggle_speech(self, item):
        """Enable/disable the random speech task."""
        self.cfg["accessibility_speech_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_all_timers()

    # ─── One-shot Dialog Helpers ────────────────────────

    def _setup_speech_timer(self, _item=None):
        """Open a dialog to configure the exact interval for random speech."""
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

    # (dialog helpers — cont.)

    def _setup_accessibility_interval(self, _item=None):
        """Open a dialog to set the exact interval for screen accessibility tasks."""
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
        """Open a dialog to set the minimum interval for random screen tasks."""
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
        """Open a dialog to set the maximum interval for random screen tasks."""
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
        """Open a dialog to set the exact interval for audio monitoring tasks."""
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
        """Open a dialog to set the minimum interval for random audio tasks."""
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
        """Open a dialog to set the maximum interval for random audio tasks."""
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
        """Open a dialog to set the minimum interval for random speech."""
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
        """Open a dialog to set the maximum interval for random speech."""
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
        """Open a dialog to set the exact interval for speech tasks."""
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

    # ─── Alarm System ───────────────────────────────────

    def _start_alarm_check(self):
        """Start a periodic GLib timer (every 30 s) that checks whether any alarm should fire."""
        self._stop_alarm_check()
        self._alarm_timer_id = GLib.timeout_add_seconds(30, self._alarm_check)
        log("alarme: verificação iniciada (a cada 30s)")

    def _stop_alarm_check(self):
        """Cancel the periodic alarm check timer."""
        if self._alarm_timer_id is not None:
            GLib.source_remove(self._alarm_timer_id)
            self._alarm_timer_id = None

    def _alarm_check(self):
        """Check every configured alarm: if the current hour+minute matches
        and it hasn't fired today, trigger it.
        Prune old fired-today entries that belong to a different date."""
        import datetime
        now = datetime.datetime.now()
        today = now.strftime("%Y-%m-%d")
        # Keep only entries whose date is still today
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
        """Activate the alarm: set dancing mood, show speech, start ringtone loop thread."""
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
        """Loop the ringtone audio file with ffplay while the alarm is ringing."""
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
        """Stop the ringing alarm: kill ffplay, reset mood, show stop message."""
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
        """Check if a chat message contains a stop-word; stop alarm if ringing.
        Called both from signal emission and directly with a text string."""
        if isinstance(_win_or_text, str):
            text = _win_or_text
        elif args:
            text = args[0]
        else:
            return
        # Portuguese + English stop words for the alarm
        stop_words = {"para", "pare", "parar", "desliga", "desligar", "cala", "calar", "stop", "chega", "silêncio", "silencio"}
        if self._alarm_ringing and any(w in text.lower() for w in stop_words):
            self._stop_alarm()

    def _toggle_alarm_item(self, item, idx):
        """Toggle the enabled state of the alarm at index *idx*."""
        alarms = self.cfg.get("alarms", [])
        if 0 <= idx < len(alarms):
            alarms[idx]["enabled"] = item.get_active()
            config.save(self.cfg)

    def _delete_alarm(self, _item, idx):
        """Remove the alarm at index *idx* from config and show a confirmation."""
        alarms = self.cfg.get("alarms", [])
        if 0 <= idx < len(alarms):
            deleted = alarms.pop(idx)
            self.cfg["alarms"] = alarms
            config.save(self.cfg)
            phrase = model.phrases.pick("ALARM_DELETED", self._("alarm_deleted_msg"))
            self.show_speech(f"{phrase} ({deleted['hour']:02d}:{deleted['minute']:02d})", 3)

    def _setup_alarm(self, _item=None):
        """Open a dialog to add a new alarm (hour, minute, optional name)."""
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

    # ─── Speech Bubble ──────────────────────────────────

    def _has_emoji(self, text):
        """Return True if *text* contains any Unicode Symbol-Other (emoji) character."""
        import unicodedata
        for ch in text:
            if unicodedata.category(ch) == "So":
                return True
        return False

    def show_speech(self, text, duration=0, from_chat=False):
        """Display a speech bubble with *text* for *duration* seconds.

        Behaviour depends on ``speech_behavior`` config:
          - "interrupt" (from chat): clears queue and shows immediately.
          - otherwise: appends to a FIFO queue shown one after another.
        Starts TTS for the text as well.
        """
        if duration <= 0:
            words = len(text.split())
            duration = max(4, min(words * 0.5, 25))

        behavior = self.cfg.get("speech_behavior", "interrupt")
        busy = self.talking_timer is not None or self.current_speech is not None
        if behavior == "interrupt" and busy:
            if from_chat:
                if self.talking_timer is not None:
                    GLib.source_remove(self.talking_timer)
                    self.talking_timer = None
                tts_mod.stop_current_audio()
                self.speech_queue.clear()
                self.current_speech = text
                self.character.set_talking(True)
                self.da.queue_draw()
                self.talking_timer = GLib.timeout_add_seconds(duration, self._clear_speech)
                self._speak_text(text)
            return

        self.speech_queue.append((text, duration))
        if self.talking_timer is None:
            self._show_next_speech()
        self._speak_text(text)

    def _add_chat_message(self, text):
        """Append *text* to the chat history file and, if the chat window is open, to the GUI."""
        text = self._strip_tool(text)
        from desktop_pet.chat import _load_history, _save_history
        history = _load_history()
        history.append({"role": "assistant", "content": text})
        _save_history(history)
        if self.chat_window is not None:
            self.chat_window.add_message(text)

    @staticmethod
    def _strip_tool(text):
        """Remove ``TOOL:`` directives from *text* (used in accessibility prompts)."""
        text = re.sub(r'(?m)^TOOL:.*$', '', text)
        text = re.sub(r'\bTOOL:\s*\S+(?:\s*\|\s*\S+)*', '', text)
        return text.strip()

    def _show_next_speech(self):
        """Pop the next item from *speech_queue* and display it.
        If the queue is empty, stop talking."""
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
        """Clear the current speech when TTS is done; schedule next queued speech."""
        if tts_mod.is_playing():
            self.talking_timer = GLib.timeout_add_seconds(2, self._clear_speech)
            return False
        self.current_speech = None
        self.character.set_talking(False)
        self.da.queue_draw()
        GLib.idle_add(self._show_next_speech)
        return False

    # ─── Drawing & Layout ───────────────────────────────

    def _get_layout(self):
        """Compute character X, bubble X, and tail direction based on window
        position, screen dimensions, bubble-side config, and character scale."""
        wx, _ = self.get_position()
        screen = self.get_screen()
        sw = screen.get_width()
        alloc = self.da.get_allocation()
        ww = alloc.width if alloc.width > 100 else WIN_W
        wh = alloc.height if alloc.height > 100 else WIN_H

        # Determine character frame dimensions for scaling
        mood, key = self.character._current_key()
        if mood is not None and mood in self.character.frames and key in self.character.frames[mood]:
            sheet = self.character.frames[mood][key]
            fw = sheet.get_width() // self.character.num_frames
            fh = sheet.get_height()
        else:
            fw, fh = 32, 32
        char_scale = min(ww / fw, wh / fh, 6.0)
        cw = int(fw * char_scale)

        # Determine which side the character stands on
        side = self.cfg.get("bubble_side", config.BUBBLE_AUTO)
        if side == config.BUBBLE_LEFT:
            on_right = True
        elif side == config.BUBBLE_RIGHT:
            on_right = False
        else:
            # Auto: character on the side farthest from screen centre
            on_right = (wx + ww // 2) > (sw // 2)

        if on_right:
            char_x = ww - cw - MARGIN
            bubble_x = MARGIN
            tail_dir = 1   # tail points right
        else:
            char_x = MARGIN
            bubble_x = MARGIN + cw + GAP
            tail_dir = -1  # tail points left

        return char_x, bubble_x, tail_dir

    def _on_draw(self, widget, cr):
        """GTK draw callback: paint wallpaper background (or transparent),
        then the character sprite, then the speech bubble."""
        w, h = widget.get_allocated_width(), widget.get_allocated_height()

        if self.cfg.get("wallpaper_enabled", False) and self._bg_surface is not None:
            bw = self._bg_surface.get_width()
            bhi = self._bg_surface.get_height()
            cr.save()
            cr.set_operator(cairo.Operator.SOURCE)
            cr.translate(0, 0)
            cr.scale(w / bw, h / bhi)
            cr.set_source_surface(self._bg_surface, 0, 0)
            cr.paint()
            cr.restore()
        else:
            cr.set_source_rgba(0, 0, 0, 0)
            cr.set_operator(cairo.Operator.SOURCE)
            cr.paint()

        cr.set_operator(cairo.Operator.OVER)

        char_x, bubble_x, tail_dir = self._get_layout()

        self.character.draw(cr, w, h, dx=char_x, dy=CHAR_Y)
        self._draw_speech_bubble(cr, bubble_x, tail_dir)

        return True

    def _draw_speech_bubble(self, cr, bx, tail_dir):
        """Draw a rounded-rectangle speech bubble with a directional tail at
        position *bx*, and render the current speech text inside it."""
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

        # Bubble background (white, slightly transparent)
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

        # Directional tail (triangle on the side where the character stands)
        tail_cy = by + bh / 2
        cr.move_to(bx if tail_dir > 0 else bx + bw, tail_cy - 6)
        cr.line_to(bx + tail_dir * 12, tail_cy)
        cr.line_to(bx if tail_dir > 0 else bx + bw, tail_cy + 6)
        cr.close_path()
        cr.set_source_rgba(1, 1, 1, 0.92)
        cr.fill()

        # Text
        cr.set_source_rgba(0.1, 0.1, 0.1, 0.95)
        cr.move_to(bx + BUBBLE_PAD, by + BUBBLE_PAD + 2)
        PangoCairo.show_layout(cr, layout)

        cr.restore()

    # ─── Mouse Events (drag, double-click) ──────────────

    def _on_button_press(self, _w, ev):
        """Handle mouse press: left button starts drag or double-click opens chat;
        right button shows context menu."""
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
        """Handle mouse release: stop dragging, save window position."""
        if ev.button == 1:
            self.dragging = False
            x, y = self.get_position()
            self.cfg["window_x"] = x
            self.cfg["window_y"] = y
            config.save(self.cfg)
        return True

    def _on_motion(self, _w, ev):
        """Handle mouse motion while dragging: move the window."""
        if self.dragging:
            self.move(
                int(ev.x_root) + self.offset_x,
                int(ev.y_root) + self.offset_y,
            )
        return True

    # ─── Context Menu ───────────────────────────────────

    def _show_context_menu(self, ev):
        """Build and show the right-click context menu with chat, alarm,
        model selection, history, settings, and quit items."""
        menu = Gtk.Menu()

        # ── Chat ─────────────────────────────────────
        chat_item = Gtk.MenuItem.new_with_label(self._("menu_chat"))
        chat_item.connect("activate", lambda _: self._open_chat())
        menu.append(chat_item)

        # ── Alarm submenu ───────────────────────────
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

        # ── Clear History ──────────────────────────
        clear_item = Gtk.MenuItem.new_with_label(self._("menu_clear_history"))
        clear_item.connect("activate", self._clear_history)
        menu.append(clear_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Settings window ──────────────────────────
        settings_item = Gtk.MenuItem.new_with_label("⚙ " + self._("menu_settings") + "...")
        settings_item.connect("activate", lambda _: self._open_settings_window())
        menu.append(settings_item)

        menu.append(Gtk.SeparatorMenuItem())

        # ── Quit ────────────────────────────────────
        quit_item = Gtk.MenuItem.new_with_label(self._("menu_quit"))
        quit_item.connect("activate", lambda _: self._on_destroy())
        menu.append(quit_item)

        menu.show_all()
        menu.popup_at_pointer(ev)

    # ─── Chat Window ────────────────────────────────────

    def _open_chat(self):
        """Open (or present) the chat window and connect its signals."""
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

    def _open_settings_window(self, _item=None):
        """Open (or present) the settings dialog window."""
        if self._settings_window is not None:
            self._settings_window.present()
            return
        self._settings_window = SettingsWindow(self)

    def _on_chat_speech(self, _win, text, mood):
        """Signal handler for ChatWindow's ``teto-speech``: show speech
        bubble, optionally set mood, and check for alarm stop words."""
        if not self._alarm_ringing:
            if mood:
                self.character.set_mood(mood)
        self.show_speech(self._strip_tool(text), from_chat=True)
        self._alarm_stop_from_chat(_win, text, mood)

    def _speak_text(self, text):
        """Send *text* to the TTS engine in a background thread.
        Strips emoji-only strings and applies voice config from model + config."""
        if not self.cfg.get("ai_enabled", True) or not self.cfg.get("tts_enabled", False):
            return
        if self._has_emoji(text):
            stripped = re.sub(r'[^\w\s,.!?;:áéíóúâêîôûãõçàèìòùäëïöüñ]', '', text).strip()
            if not stripped:
                return
            text = stripped
        voice_config = dict(getattr(model, "TTS_VOICE", {}))
        if not voice_config:
            return
        fish_voice = self.cfg.get("fish_audio_voice", "")
        if fish_voice:
            voice_config["fish_audio"] = fish_voice
        provider = self.cfg.get("tts_provider", "auto")
        api_key = self.cfg.get("fish_audio_key", "") or None
        device = self.cfg.get("tts_device", "") or None
        self._last_tts_time = time.time()
        threading.Thread(
            target=tts_mod.speak,
            args=(text, provider, voice_config, api_key, device),
            daemon=True,
        ).start()

    def _on_chat_closed(self, _w=None):
        """Clear reference to the closed chat window."""
        self.chat_window = None

    def _clear_history(self, _item=None):
        """Clear the chat history file and show confirmation."""
        if self.chat_window is not None:
            self.chat_window.clear_history()
        else:
            try:
                path = os.path.expanduser(f"~/.config/teto-pet/history/{model.MODEL_ID}.json")
                os.remove(path)
            except OSError:
                pass
        self.show_speech(self._("history_cleared"), 3)

    # ─── Settings Window ─────────────────────────────────

    def _toggle_ontop(self, item=None):
        """Toggle the 'always on top' window hint."""
        if item is not None:
            self.cfg["always_on_top"] = item.get_active()
            self.set_keep_above(item.get_active())
        else:
            self.set_keep_above(self.cfg.get("always_on_top", True))
        config.save(self.cfg)

    def _change_speech_behavior(self, item=None, key=None):
        """Change the speech-queueing behaviour ("queue" vs "interrupt")."""
        if item is not None and not item.get_active():
            return
        if key is None:
            return
        self.cfg["speech_behavior"] = key
        config.save(self.cfg)

    def _toggle_wallpaper(self, item=None):
        """Toggle wallpaper / full-screen overlay mode."""
        if item is not None:
            self.cfg["wallpaper_enabled"] = item.get_active()
            config.save(self.cfg)
        enabled = self.cfg.get("wallpaper_enabled", False)
        if enabled and self._bg_surface is not None:
            self.set_resizable(True)
            self._apply_wallpaper()
        else:
            self.unfullscreen()
            self.unmaximize()
            self.set_default_size(WIN_W, WIN_H)
            self.resize(WIN_W, WIN_H)
            self.set_resizable(False)
            self.move(self.cfg.get("window_x", 100), self.cfg.get("window_y", 100))
        self.da.queue_draw()

    def _apply_wallpaper_if_enabled(self):
        """Resize to full screen if wallpaper mode is on (called once at startup)."""
        if self.cfg.get("wallpaper_enabled", False):
            self._apply_wallpaper()

    def _apply_wallpaper(self):
        """Resize the window to fill the primary monitor for the wallpaper overlay."""
        if self._bg_surface is None:
            return
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        if monitor is None:
            monitor = display.get_monitor(0)
        geo = monitor.get_geometry()
        self.set_default_size(geo.width, geo.height)
        self.resize(geo.width, geo.height)
        self.move(geo.x, geo.y)
        log("BG: wallpaper mode ativado %dx%d", geo.width, geo.height)
        self.da.queue_draw()

    def _load_background(self):
        """Search for a background image (background.jpg/png) in the model
        directory or alongside the script and load it as a cairo surface."""
        self._bg_surface = None
        search_dirs = [
            model.MODEL_DIR,
            os.path.dirname(os.path.abspath(__file__)),
        ]
        for search_dir in search_dirs:
            for ext in ("jpg", "jpeg", "png"):
                path = os.path.join(search_dir, f"background.{ext}")
                log("BG: checking %s", path)
                if os.path.exists(path):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                        self._bg_surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 1, None)
                        log("BG: loaded %s (%dx%d)", path,
                            self._bg_surface.get_width(), self._bg_surface.get_height())
                    except Exception as e:
                        log("BG: erro ao carregar %s: %s", path, e)
                    return
        log("BG: nenhum background.jpg/.png encontrado em %s", search_dirs)

    def _toggle_ai_enabled(self, item=None, enabled=None):
        """Enable/disable all AI-dependent features. Saves a backup of
        affected settings so they can be restored on re-enable."""
        if enabled is None:
            if item is not None:
                enabled = item.get_active()
            else:
                enabled = not self.cfg.get("ai_enabled", True)
        self.cfg["ai_enabled"] = enabled
        if not enabled:
            self._ai_backup = {
                "ai_provider": self.cfg.get("ai_provider"),
                "tts_enabled": self.cfg.get("tts_enabled", False),
                "mic_stt_enabled": self.cfg.get("mic_stt_enabled", False),
                "accessibility_enabled": self.cfg.get("accessibility_enabled", False),
                "accessibility_audio_enabled": self.cfg.get("accessibility_audio_enabled", False),
            }
            self.cfg["ai_provider"] = config.PROVIDER_PHRASES
            self.cfg["tts_enabled"] = False
            self.cfg["mic_stt_enabled"] = False
            self.cfg["accessibility_enabled"] = False
            self.cfg["accessibility_audio_enabled"] = False
        else:
            backup = getattr(self, '_ai_backup', None)
            if backup:
                self.cfg["ai_provider"] = backup["ai_provider"]
                self.cfg["tts_enabled"] = backup["tts_enabled"]
                self.cfg["mic_stt_enabled"] = backup["mic_stt_enabled"]
                self.cfg["accessibility_enabled"] = backup["accessibility_enabled"]
                self.cfg["accessibility_audio_enabled"] = backup["accessibility_audio_enabled"]
            self._ai_backup = None
        config.save(self.cfg)
        self._start_mic_listener()
        self._start_all_timers()
        self._update_ai_sensitivity()

    def _update_ai_sensitivity(self):
        """Enable/disable menu items whose sensitivity depends on AI being active."""
        enabled = self.cfg.get("ai_enabled", True)
        for item in self._ai_sensitive_items:
            item.set_sensitive(enabled)

    def _toggle_tool(self, item, key):
        """Generic boolean config toggle bound to a Gtk.CheckMenuItem."""
        self.cfg[key] = item.get_active()
        config.save(self.cfg)

    def _toggle_mic_stt(self, item):
        """Enable/disable the microphone STT listener."""
        self.cfg["mic_stt_enabled"] = item.get_active()
        config.save(self.cfg)
        self._start_mic_listener()

    def _toggle_tts(self, item):
        """Enable/disable text-to-speech."""
        self.cfg["tts_enabled"] = item.get_active()
        config.save(self.cfg)

    def _change_tts_provider(self, item=None, provider=None):
        """Switch the active TTS provider (e.g. "auto", "fish", "system")."""
        if item is not None and not item.get_active():
            return
        if provider is None:
            return
        self.cfg["tts_provider"] = provider
        config.save(self.cfg)

    # ─── TTS (Text-to-Speech) ────────────────────────────

    def _setup_tts_device(self, _item=None):
        """Open a dialog to select the audio output device for TTS playback."""
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

    def _setup_tts_volume(self, _item=None):
        """Open a dialog to adjust the TTS volume (0-100)."""
        current = self.cfg.get("tts_volume", 100)
        dialog = Gtk.Dialog(
            title=self._("tts_volume_title"),
            transient_for=self, flags=0,
        )
        dialog.add_buttons(self._("btn_cancel"), Gtk.ResponseType.CANCEL, self._("btn_ok"), Gtk.ResponseType.OK)
        dialog.set_default_size(350, 140)
        area = dialog.get_content_area()
        area.set_margin_start(12); area.set_margin_end(12)
        area.set_margin_top(12); area.set_margin_bottom(12)
        lbl = Gtk.Label(label=self._("tts_volume_label"))
        lbl.set_xalign(0); area.pack_start(lbl, False, False, 6)

        adj = Gtk.Adjustment(value=current, lower=0, upper=100, step_increment=1, page_increment=10)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(0)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_hexpand(True)
        area.pack_start(scale, False, False, 4)

        area.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.cfg["tts_volume"] = int(adj.get_value())
            config.save(self.cfg)
        dialog.destroy()

    def _setup_fish_audio(self, _item=None):
        """Open a dialog to configure Fish Audio TTS (API key + voice ID)."""
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

    # ─── Mic / STT (Speech-to-Text) ─────────────────────

    def _change_mic_stt_mode(self, item=None, mode=None):
        """Switch STT mode ("toggle" for continuous listening, "hold" for push-to-talk)."""
        if item is not None and not item.get_active():
            return
        if mode is None:
            return
        self.cfg["mic_stt_mode"] = mode
        config.save(self.cfg)
        self._start_mic_listener()

    def _start_mic_listener(self):
        """Start the periodic GLib timer for continuous (toggle-mode) mic listening."""
        self._stop_mic_listener()
        if not self.cfg.get("mic_stt_enabled") or self.cfg.get("mic_stt_mode") != "toggle":
            return
        self._mic_listener_timer = GLib.timeout_add_seconds(8, self._mic_listen_tick)
        log("STT: listener contínuo iniciado")

    def _stop_mic_listener(self):
        """Cancel the continuous mic listener timer."""
        if self._mic_listener_timer is not None:
            GLib.source_remove(self._mic_listener_timer)
            self._mic_listener_timer = None
        self._mic_listening = False

    def _mic_listen_tick(self):
        """Timer tick for continuous STT: record 5 s of audio, transcribe,
        and send to chat.  Filters echo (TTS self-talk) and repeated text."""
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
        """Thread target: capture mic audio, transcribe via STT AI,
        filter out echo / repeats, and forward to chat."""
        try:
            wav = listen_mic(device=device, duration=5)
            if isinstance(wav, str) and wav.startswith("Erro"):
                log("STT contínuo: erro na captura: %s", wav)
                return
            if not wav:
                return
            if not self.cfg.get("ai_enabled", True):
                return
            text = ai.transcribe(wav)
            # Only process text that contains at least one letter character
            if text and re.search(r'[a-zA-Záéíóúâêîôûãõçàèìòùäëïöüñ]', text):
                text = text.strip()
                # Ignore echoes from our own TTS output (within 1.5 s)
                if time.time() - self._last_tts_time < 1.5:
                    log("STT contínuo: ignorado (eco TTS): %s", text)
                    return
                # Ignore consecutive identical transcriptions
                if text == getattr(self, '_last_stt_text', ''):
                    log("STT contínuo: ignorado (repetido): %s", text)
                    return
                self._last_stt_text = text
                log("STT contínuo: %s", text)
                GLib.idle_add(self._handle_mic_speech, text)
        finally:
            self._mic_listening = False

    def _handle_mic_speech(self, text):
        """Route transcribed speech to the chat window for AI processing."""
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

    # ─── Global Hotkey (Win+V) ──────────────────────────

    def _start_ptt_socket_server(self):
        """Create a UNIX socket server for external push-to-talk commands,
        and write the helper script that external tools (or DE shortcuts)
        call to send "press" / "release" / "toggle" commands."""
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
        """Write a bash helper script (``mate-helper-ptt``) that sends commands
        to the UNIX socket.  Used by desktop environment global shortcuts."""
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
        """Accept commands from the PTT UNIX socket in a daemon thread:
        "press" starts recording, "release" stops, "toggle" flips."""
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
        """Start a pynput keyboard listener for the global Win+V shortcut.
        Only works if pynput is available."""
        if not HAS_PYNPUT:
            return
        if self._global_hotkey_listener is not None:
            return

        def on_press(key):
            self._global_keys_state.add(key)
            # Check for Super (Cmd/Win) + V combination
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
        """Start STT recording when the global shortcut is pressed (hold mode only)."""
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
        """Stop STT recording when the global shortcut is released."""
        if not self._global_recording:
            return
        self._global_recording = False
        if self._stt_shortcut_stop_event is not None:
            self._stt_shortcut_stop_event.set()

    # ─── Keyboard Shortcut (in-app STT) ─────────────────

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
            if not self.cfg.get("ai_enabled", True):
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

    # ─── Window Size ────────────────────────────────────

    def _setup_window_scale(self, _item=None):
        """Open a dialog to adjust the window zoom/scale factor (3-10)."""
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
        """Resize the window to match *scale* and update config."""
        cw = 32 * scale
        ww = MARGIN + cw + GAP + BUBBLE_MAX + MARGIN
        wh = 32 * scale + 50
        self.set_default_size(ww, wh)
        self.resize(ww, wh)
        self.da.queue_draw()
        if self.chat_window is not None and self.chat_window.get_visible():
            self.chat_window.resize(max(400, ww - 40), self.chat_window.get_allocation().height)
        self.cfg["window_scale"] = scale
        config.save(self.cfg)

    # ─── Language / Model / Bubble Side ─────────────────

    def _change_bubble_side(self, item=None, side=None):
        """Change which side the speech bubble appears on (left, right, or auto)."""
        if item is not None and not item.get_active():
            return
        if side is None:
            return
        self.cfg["bubble_side"] = side
        config.save(self.cfg)
        self.da.queue_draw()

    def _change_language(self, item=None, lang_code=None):
        """Switch the UI language and restart the application."""
        if item is not None and not item.get_active():
            return
        if lang_code is None:
            return
        self.cfg["language"] = lang_code
        config.save(self.cfg)
        self.show_speech("OK! ^_^")
        GLib.timeout_add(1500, self._restart)

    def _change_model(self, item=None, model_name=None):
        """Switch the active character/model and restart the application."""
        if item is not None and not item.get_active():
            return
        self.cfg["active_model"] = model_name
        config.save(self.cfg)
        self.show_speech(self._("restarting_model", model=model_name.replace("_", " ").title()))
        GLib.timeout_add(1500, self._restart)

    def _restart(self):
        """Save position and relaunch the application, then quit."""
        x, y = self.get_position()
        self.cfg["window_x"] = x
        self.cfg["window_y"] = y
        config.save(self.cfg)
        import __main__
        main = os.path.abspath(__main__.__file__)
        log("RESTART %s %s", sys.executable, main)
        subprocess.Popen([sys.executable, main])
        Gtk.main_quit()
        return False

    # ─── API Key Dialogs (Gemini, Groq, HF, Fish) ───────

    def _setup_gemini(self):
        """Open a dialog to enter a Google Gemini API key."""
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
        """Open a dialog to enter a Groq API key."""
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
        """Open a dialog to enter a HuggingFace API token."""
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
        """Fetch the list of available Ollama models from the local API."""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                return sorted(m["name"] for m in resp.json().get("models", []))
        except Exception:
            pass
        return []

    def _change_ollama_model(self, item=None, model_name=None):
        """Switch the active Ollama model."""
        if item is not None and not item.get_active():
            return
        if model_name is None:
            return
        self.cfg["ollama_model"] = model_name
        config.save(self.cfg)

    def _change_provider(self, item=None, provider=None):
        """Switch the AI provider (auto, ollama, gemini, groq, phrases).
        Opens the corresponding API-key setup dialog if needed."""
        if item is not None and not item.get_active():
            return
        if provider is None:
            return
        self.cfg["ai_provider"] = provider
        config.save(self.cfg)
        if provider == config.PROVIDER_GEMINI and not self.cfg.get("gemini_key"):
            GLib.idle_add(self._setup_gemini)
        if provider == config.PROVIDER_GROQ and not self.cfg.get("groq_key"):
            GLib.idle_add(self._setup_groq)
        if provider in (config.PROVIDER_AUTO, config.PROVIDER_OLLAMA):
            GLib.idle_add(lambda: ollama_ensure_running())

    # ─── Profile / About ────────────────────────────────

    def _setup_profile(self):
        """Open a dialog to edit the user profile (name and bio)."""
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
        """Show the standard GTK About dialog."""
        about = Gtk.AboutDialog()
        about.set_program_name("Mate Helper")
        about.set_version("0.1.0")
        about.set_comments(self._("about_comments"))
        about.set_copyright("MCookinho")
        about.set_license("MIT")
        about.set_transient_for(self)
        about.run()
        about.destroy()

    # ─── Cleanup ────────────────────────────────────────

    def _on_destroy(self, _w=None):
        """Clean up all resources: save config, stop timers, terminate
        alarm, kill audio capture processes, stop global hotkey listener,
        remove the UNIX socket, stop Ollama, and quit GTK."""
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
