"""Settings window for Mate Helper desktop pet.

Provides a multi-tab GTK dialog (Notebook) for configuring all aspects of the
application: appearance, voice output, microphone input, AI provider and
permissions, desktop automation/accessibility timers, alarms, and an about
page with credits.  Settings are stored in a shared config dictionary and
persisted via config.save().
"""

import gi

gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Pango

from desktop_pet import config
from desktop_pet.models import list_models
from desktop_pet import tts as tts_mod
from desktop_pet.tools import list_mic_sources


class SettingsWindow(Gtk.Window):
    """GTK settings dialog with notebook tabs for all application configuration."""

    # ── Window Lifecycle ────────────────────────────────────────────────

    def _(self, key, **kwargs):
        """Translate *key* via the parent window's i18n helper.

        Parameters
        ----------
        key : str
            Translation lookup key.
        **kwargs
            Optional format arguments passed to the parent translator.
        """
        return self.parent._(key, **kwargs)

    def __init__(self, parent):
        """Build and show the settings window.

        Parameters
        ----------
        parent : desktop_pet.PetWindow
            The main application window that owns this dialog.
        """
        self.parent = parent
        super().__init__(title="\u2699 " + self._("menu_settings"))
        self.cfg = parent.cfg
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(920, 680)
        self.set_resizable(True)
        self.connect("destroy", self._on_destroy)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self._apply_pixel_css()
        self._setup_ui()

        self.show_all()
        self._refresh_inteligencia_visibility()

    def _apply_pixel_css(self):
        """Apply a pixel-font CSS stylesheet to the window and its tab labels."""
        css = b"""
#settings-window label {
    font-family: monospace;
    font-size: 16px;
}
#settings-window .dim-label {
    font-size: 13px;
}
#settings-window button {
    font-size: 14px;
}
#settings-window switch {
    font-size: 14px;
}
#settings-window scale {
    font-size: 14px;
}
#settings-window combobox {
    font-size: 14px;
}
#settings-window combobox text {
    font-size: 14px;
}
#settings-window entry {
    font-size: 14px;
}
notebook tab label {
    font-family: monospace;
    font-size: 14px;
}
"""
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        self.set_name("settings-window")
        screen = self.get_screen()
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_destroy(self, _w=None):
        """Clean up the parent's reference and destroy the window."""
        self.parent._settings_window = None
        self.destroy()

    def _setup_ui(self):
        """Create the notebook widget and populate each tab page."""
        nb = Gtk.Notebook()
        nb.set_scrollable(True)
        nb.set_tab_pos(Gtk.PositionType.TOP)
        nb.set_margin_top(8)

        pages = [
            (self._("menu_appearance"), self._build_geral),
            (self._("menu_voice"), self._build_voz),
            (self._("menu_microphone"), self._build_microfone),
            (self._("menu_intelligence"), self._build_inteligencia),
            (self._("menu_automation"), self._build_automacao),
            (self._("menu_about"), self._build_sobre),
        ]
        for label_text, builder in pages:
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_propagate_natural_height(True)
            content = builder()
            sw.add(content)
            label = Gtk.Label(label=label_text)
            nb.append_page(sw, label)

        self.add(nb)

    # ── UI Helpers ──────────────────────────────────────────────────────

    def _box(self):
        """Return a vertically-oriented Gtk.Box with standard margins."""
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        b.set_margin_start(20)
        b.set_margin_end(20)
        b.set_margin_top(16)
        b.set_margin_bottom(16)
        return b

    def _section(self, box, text):
        """Append a bold section header label to *box*.

        Parameters
        ----------
        box : Gtk.Box
            The container to pack into.
        text : str
            The header text (rendered as bold markup).
        """
        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{text}</b>")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_top(12)
        box.pack_start(lbl, False, False, 0)

    def _desc(self, box, text):
        """Append a dimmed description label to *box*.

        Parameters
        ----------
        box : Gtk.Box
            The container to pack into.
        text : str
            The description text.
        """
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class("dim-label")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_bottom(2)
        lbl.set_line_wrap(True)
        lbl.set_xalign(0.0)
        box.pack_start(lbl, False, False, 0)

    def _row(self, box, label_text, widget, desc_text=None):
        """Append a label + widget row (with optional description) to *box*.

        Parameters
        ----------
        box : Gtk.Box
            The parent container.
        label_text : str
            Left-aligned label for the row.
        widget : Gtk.Widget
            The interactive control for this row.
        desc_text : str or None
            Optional extra description shown below the widget.
        """
        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hb.set_margin_top(4)

        lbl = Gtk.Label(label=label_text)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_xalign(0.0)
        lbl.set_size_request(160, -1)

        wbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wbox.pack_start(widget, False, False, 0)
        if desc_text:
            dlbl = Gtk.Label(label=desc_text)
            dlbl.get_style_context().add_class("dim-label")
            dlbl.set_halign(Gtk.Align.START)
            dlbl.set_xalign(0.0)
            dlbl.set_line_wrap(True)
            dlbl.set_margin_top(1)
            wbox.pack_start(dlbl, False, False, 0)

        hb.pack_start(lbl, False, False, 0)
        hb.pack_start(wbox, True, True, 0)
        box.pack_start(hb, False, False, 0)

    def _sep(self, box):
        """Append a horizontal separator to *box*."""
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(8)
        sep.set_margin_bottom(4)
        box.pack_start(sep, False, False, 0)

    def _save(self):
        """Persist the current config dictionary to disk."""
        config.save(self.cfg)

    def _switch_row(self, box, label, desc, key, callback=None):
        """Build a labelled Gtk.Switch row bound to *key* in the config.

        Parameters
        ----------
        box : Gtk.Box
            The parent container.
        label : str
            Row label text.
        desc : str or None
            Optional description text.
        key : str
            Config key the switch controls.
        callback : callable or None
            Optional callback(state) fired on toggle.

        Returns
        -------
        Gtk.Switch
        """
        sw = Gtk.Switch()
        sw.set_active(self.cfg.get(key, False))
        sw.set_halign(Gtk.Align.START)

        def on_switch(switch, pspec):
            state = switch.get_active()
            self.cfg[key] = state
            self._save()
            if callback:
                callback(state)

        sw.connect("notify::active", on_switch)
        self._row(box, label, sw, desc)
        return sw

    def _combo_row(
        self, box, label, desc, items, get_active, on_change, disabled_ids=None
    ):
        """Build a labelled Gtk.ComboBox row.

        Parameters
        ----------
        box : Gtk.Box
            The parent container.
        label : str
            Row label text.
        desc : str or None
            Optional description text.
        items : list of (id, display_label)
            The combo-box items.
        get_active : callable
            Returns the currently active item id.
        on_change : callable
            Called with the new item id on selection.
        disabled_ids : container or None
            Item ids that should appear as insensitive.

        Returns
        -------
        Gtk.ComboBox
        """
        store = Gtk.ListStore(str, str, bool)
        combo = Gtk.ComboBox(model=store)
        combo.set_halign(Gtk.Align.START)
        for item_id, item_label in items:
            sensitive = disabled_ids is None or item_id not in disabled_ids
            store.append([str(item_id), item_label, sensitive])

        renderer = Gtk.CellRendererText()
        renderer.set_property("font-desc", Pango.FontDescription("monospace 14"))
        combo.pack_start(renderer, True)
        combo.add_attribute(renderer, "text", 1)
        combo.add_attribute(renderer, "sensitive", 2)

        combo.set_id_column(0)

        def on_combo(cb):
            val = cb.get_active_id()
            if val is not None:
                on_change(val)

        combo.connect("changed", on_combo)
        combo.handler_block_by_func(on_combo)
        combo.set_active_id(str(get_active()))
        combo.handler_unblock_by_func(on_combo)
        self._row(box, label, combo, desc)
        return combo

    def _scale_row(
        self, box, label, desc, key, min_v, max_v, step=1, fmt="%d", callback=None
    ):
        """Build a labelled horizontal Gtk.Scale row.

        Parameters
        ----------
        box : Gtk.Box
            The parent container.
        label : str
            Row label text.
        desc : str or None
            Optional description text.
        key : str
            Config key the scale controls.
        min_v : int
            Minimum value.
        max_v : int
            Maximum value.
        step : int
            Step increment.
        fmt : str
            Format string for the value readout label.
        callback : callable or None
            Optional callback(value) on change.

        Returns
        -------
        Gtk.Scale
        """
        adj = Gtk.Adjustment(
            self.cfg.get(key, min_v), min_v, max_v, step, step * 5, 0
        )
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_digits(0)
        scale.set_size_request(200, -1)
        scale.set_halign(Gtk.Align.START)

        val_lbl = Gtk.Label(label=fmt % self.cfg.get(key, min_v))
        val_lbl.set_width_chars(4)
        val_lbl.set_xalign(0.5)

        hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hb.pack_start(scale, False, False, 0)
        hb.pack_start(val_lbl, False, False, 0)

        def on_change(w, *a):
            v = int(adj.get_value())
            self.cfg[key] = v
            self._save()
            val_lbl.set_text(fmt % v)
            if callback:
                callback(v)

        adj.connect("value-changed", on_change)
        self._row(box, label, hb, desc)
        return scale

    def _spin_row(self, box, label, desc, key, min_v, max_v, step=1):
        """Build a labelled Gtk.SpinButton row.

        Parameters
        ----------
        box : Gtk.Box
            The parent container.
        label : str
            Row label text.
        desc : str or None
            Optional description text.
        key : str
            Config key the spin button controls.
        min_v : int
            Minimum value.
        max_v : int
            Maximum value.
        step : int
            Step increment.

        Returns
        -------
        Gtk.SpinButton
        """
        v = self.cfg.get(key, min_v)
        adj = Gtk.Adjustment(v, min_v, max_v, step, step * 5, 0)
        spin = Gtk.SpinButton(adjustment=adj)
        spin.set_numeric(True)
        spin.set_halign(Gtk.Align.START)

        def on_change(w):
            val = int(spin.get_value())
            self.cfg[key] = val
            self._save()

        spin.connect("value-changed", on_change)
        self._row(box, label, spin, desc)
        return spin

    def _btn_row(self, box, label, btn_label, desc, callback):
        """Build a labelled Gtk.Button row.

        Parameters
        ----------
        box : Gtk.Box
            The parent container.
        label : str
            Row label text.
        btn_label : str
            Text shown on the button.
        desc : str or None
            Optional description text.
        callback : callable
            Called when the button is clicked.

        Returns
        -------
        Gtk.Button
        """
        btn = Gtk.Button(label=btn_label)
        btn.set_halign(Gtk.Align.START)
        btn.connect("clicked", callback)
        self._row(box, label, btn, desc)
        return btn

    # ── Tab: Appearance ────────────────────────────────────────────────

    def _build_geral(self):
        """Build the Appearance tab content.

        Includes: always-on-top, wallpaper, window scale, speech bubble
        positioning, speech behaviour, model selection, and language.
        """
        box = self._box()

        self._section(box, self._("settings_window"))
        self._desc(box, self._("settings_appearance_desc"))

        def _ontop(state):
            self.parent.set_keep_above(state)

        self._switch_row(
            box,
            self._("menu_always_on_top"),
            self._("settings_always_on_top_desc"),
            "always_on_top",
            _ontop,
        )

        def _wall(state):
            self.parent._toggle_wallpaper(None)

        self._switch_row(
            box,
            self._("menu_wallpaper"),
            self._("settings_wallpaper_desc"),
            "wallpaper_enabled",
            _wall,
        )

        self._scale_row(
            box,
            self._("window_scale_title"),
            self._("settings_pet_size_scale"),
            "window_scale",
            3,
            10,
            callback=lambda v: self.parent._apply_window_scale(v),
        )

        self._sep(box)
        self._section(box, self._("settings_bubble"))
        self._desc(box, self._("settings_bubble_desc"))

        def _bubble(side):
            self.cfg["bubble_side"] = side
            self._save()
            self.parent.cfg["bubble_side"] = side
            self.parent.da.queue_draw()

        self._combo_row(
            box,
            self._("menu_bubble_side"),
            self._("settings_bubble_side_desc"),
            [
                ("auto", self._("menu_bubble_auto")),
                ("left", self._("menu_bubble_left")),
                ("right", self._("menu_bubble_right")),
            ],
            lambda: self.cfg.get("bubble_side", "auto"),
            _bubble,
        )

        def _behavior(behav):
            self.cfg["speech_behavior"] = behav
            self._save()

        self._combo_row(
            box,
            self._("menu_speech_behavior"),
            self._("settings_speech_behavior_desc"),
            [
                ("interrupt", self._("menu_speech_interrupt")),
                ("wait", self._("menu_speech_wait")),
            ],
            lambda: self.cfg.get("speech_behavior", "interrupt"),
            _behavior,
        )

        self._sep(box)
        self._section(box, self._("settings_model"))
        self._desc(box, self._("settings_model_desc"))

        def _model(m):
            self.parent._change_model(None, m)

        models = list_models()
        self._combo_row(
            box,
            self._("menu_model"),
            self._("settings_model_item_desc"),
            [(m, m.replace("_", " ").title()) for m in models],
            lambda: self.cfg.get("active_model", "kasane_teto"),
            _model,
        )

        self._sep(box)
        self._section(box, self._("settings_language"))
        self._desc(box, self._("settings_language_desc"))

        def _lang(code):
            self.parent._change_language(None, code)

        self._combo_row(
            box,
            self._("settings_language"),
            self._("settings_language_restart"),
            [
                ("pt", self._("lang_pt")),
                ("en", self._("lang_en")),
                ("jp", self._("lang_jp")),
            ],
            lambda: self.cfg.get("language", "pt"),
            _lang,
        )

        return box

    # ── Tab: Voice ──────────────────────────────────────────────────────

    def _build_voz(self):
        """Build the Voice tab content.

        Includes: TTS enable switch, provider selection, output device,
        volume scale, and Fish Audio API key configuration button.
        """
        box = self._box()

        self._section(box, self._("settings_voice_section"))
        self._desc(box, self._("settings_voice_desc"))

        def _tts(state):
            self.cfg["tts_enabled"] = state
            self._save()

        self._switch_row(
            box,
            self._("menu_tts"),
            self._("settings_voice_enable_desc"),
            "tts_enabled",
            _tts,
        )

        self._sep(box)
        self._section(box, self._("settings_voice_provider_section"))
        self._desc(box, self._("settings_voice_provider_choose"))

        def _tts_prov(prov):
            self.cfg["tts_provider"] = prov
            self._save()

        self._tts_provider_combo = self._combo_row(
            box,
            self._("menu_tts_provider"),
            self._("settings_voice_provider_desc"),
            [
                ("auto", self._("tts_provider_auto")),
                ("fish_audio", self._("tts_provider_fish")),
                ("edge_tts", self._("tts_provider_edge")),
                ("pyttsx3", self._("tts_provider_pyttsx")),
            ],
            lambda: self.cfg.get("tts_provider", "auto"),
            _tts_prov,
        )

        tts_devices = tts_mod.list_audio_devices()
        if tts_devices:

            def _tts_dev(dev_id):
                self.cfg["tts_device"] = dev_id if dev_id else ""
                self._save()

            items = [("", self._("system_default"))]
            items += [(str(d["id"]), d["description"]) for d in tts_devices]
            self._combo_row(
                box,
                self._("menu_tts_device"),
                self._("settings_output_device_desc"),
                items,
                lambda: self.cfg.get("tts_device", ""),
                _tts_dev,
            )

        self._scale_row(
            box,
            self._("menu_tts_volume"),
            self._("settings_voice_volume_desc"),
            "tts_volume",
            0,
            100,
        )

        self._sep(box)
        self._section(box, self._("settings_fish_section"))
        self._desc(box, self._("settings_fish_desc"))

        self._btn_row(
            box,
            self._("settings_api_key"),
            self._("settings_configure_fish"),
            self._("settings_fish_configure_desc"),
            lambda *a: self.parent._setup_fish_audio(),
        )

        return box

    # ── Tab: Microphone ─────────────────────────────────────────────────

    def _build_microfone(self):
        """Build the Microphone tab content.

        Includes: mic/STT enable switch, input mode (hold/toggle), source
        device selection, shortcut configuration, and global shortcut help.
        """
        box = self._box()

        self._section(box, self._("settings_mic_section"))
        self._desc(box, self._("settings_mic_desc"))

        def _mic(state):
            self.cfg["mic_stt_enabled"] = state
            self._save()
            self.parent._start_mic_listener()

        self._switch_row(
            box,
            self._("enable_microphone"),
            self._("settings_mic_enable_desc"),
            "mic_stt_enabled",
            _mic,
        )

        self._sep(box)
        self._section(box, self._("settings_mic_mode_section"))
        self._desc(box, self._("settings_mic_mode_desc"))

        def _mic_mode(mode):
            self.cfg["mic_stt_mode"] = mode
            self._save()
            self.parent._start_mic_listener()

        self._combo_row(
            box,
            self._("settings_mic_mode"),
            self._("settings_mic_mode_choose_desc"),
            [
                ("hold", self._("menu_hold_to_talk")),
                ("toggle", self._("menu_mic_open")),
            ],
            lambda: self.cfg.get("mic_stt_mode", "toggle"),
            _mic_mode,
        )

        mic_sources = list_mic_sources()
        if mic_sources:

            def _mic_dev(dev_name):
                self.cfg["mic_stt_device"] = dev_name
                self._save()

            items = [("", self._("system_default"))] + [(s, s) for s in mic_sources]
            self._combo_row(
                box,
                self._("settings_mic_device"),
                self._("settings_mic_device_desc"),
                items,
                lambda: self.cfg.get("mic_stt_device", ""),
                _mic_dev,
            )

        self._sep(box)
        self._section(box, self._("settings_shortcuts_section"))
        self._desc(box, self._("settings_shortcuts_desc"))

        self._btn_row(
            box,
            self._("menu_mic_shortcut"),
            self._("settings_configure_shortcut"),
            self._("settings_mic_shortcut_desc"),
            lambda *a: self.parent._setup_stt_shortcut(),
        )

        self._btn_row(
            box,
            self._("menu_global_shortcut"),
            self._("settings_global_help"),
            self._("settings_global_shortcut_desc"),
            lambda *a: self.parent._show_global_shortcut_help(),
        )

        return box

    # ── Tab: AI ─────────────────────────────────────────────────────────

    def _build_inteligencia(self):
        """Build the AI / Intelligence tab content.

        Includes: AI enable switch, provider selection, API-key buttons for
        Gemini/Groq/HuggingFace, Ollama model list, user profile editing,
        and per-permission toggles (file read/write, command execution, etc).
        """
        box = self._box()

        self._section(box, self._("settings_ai_section"))
        self._desc(box, self._("settings_ai_desc"))

        def _ai(state):
            self.parent._toggle_ai_enabled(enabled=state)
            self._refresh_inteligencia_visibility()

        self._switch_row(
            box,
            self._("menu_ai_enable"),
            self._("settings_ai_enabled_desc"),
            "ai_enabled",
            _ai,
        )

        ai_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._ai_controls_box = ai_box

        self._section(ai_box, self._("settings_ai_provider_section"))
        self._desc(ai_box, self._("settings_ai_provider_desc"))

        def _prov(p):
            self.parent._change_provider(None, p)

        self._combo_row(
            ai_box,
            self._("menu_ai_provider"),
            self._("settings_ai_provider_choose_desc"),
            [
                ("auto", self._("menu_provider_auto")),
                ("groq", self._("menu_provider_groq")),
                ("gemini", self._("menu_provider_gemini")),
                ("huggingface", self._("menu_provider_hf")),
                ("ollama", self._("menu_provider_ollama")),
                ("phrases", self._("menu_provider_phrases")),
            ],
            lambda: self.cfg.get("ai_provider", "auto"),
            _prov,
        )

        self._sep(ai_box)
        self._section(ai_box, self._("settings_api_keys_section"))
        self._desc(ai_box, self._("settings_api_keys_desc"))

        self._btn_row(
            ai_box,
            self._("settings_gemini_label"),
            self._("menu_configure_gemini"),
            self._("settings_gemini_btn_desc"),
            lambda *a: self.parent._setup_gemini(),
        )
        self._btn_row(
            ai_box,
            self._("settings_groq_label"),
            self._("menu_configure_groq"),
            self._("settings_groq_btn_desc"),
            lambda *a: self.parent._setup_groq(),
        )
        self._btn_row(
            ai_box,
            self._("settings_hf_label"),
            self._("menu_configure_hf"),
            self._("settings_hf_btn_desc"),
            lambda *a: self.parent._setup_hf(),
        )

        ollama_models = self.parent._list_ollama_models()
        if ollama_models:
            self._sep(ai_box)
            self._section(ai_box, self._("settings_ollama_section"))
            self._desc(ai_box, self._("settings_ollama_desc"))

            def _ollama(m):
                self.parent._change_ollama_model(None, m)

            self._combo_row(
                ai_box,
                self._("menu_ollama_model"),
                self._("settings_ollama_model_desc"),
                [(m, m) for m in ollama_models],
                lambda: self.cfg.get(
                    "ollama_model", ollama_models[0] if ollama_models else ""
                ),
                _ollama,
            )

        box.pack_start(ai_box, False, False, 0)

        # Profile and permissions are always visible (even with AI off)
        self._sep(box)
        self._section(box, self._("settings_profile_section"))
        self._desc(box, self._("settings_profile_desc"))

        self._btn_row(
            box,
            self._("settings_my_profile"),
            self._("settings_edit_profile"),
            self._("settings_profile_btn_desc"),
            lambda *a: self.parent._setup_profile(),
        )

        self._sep(box)
        self._section(box, self._("settings_permissions_section"))
        self._desc(box, self._("settings_permissions_desc"))

        for key, label in [
            ("tool_read_file", self._("menu_perm_read_file")),
            ("tool_list_files", self._("menu_perm_list_files")),
            ("tool_run_command", self._("menu_perm_run_command")),
            ("tool_write_file", self._("menu_perm_write_file")),
            ("tool_screenshot", self._("menu_perm_screenshot")),
            ("tool_open_url", self._("menu_perm_open_url")),
            ("tool_listen", self._("menu_perm_listen")),
        ]:

            def make_cb(k):
                def cb(state):
                    self.cfg[k] = state
                    self._save()

                return cb

            self._switch_row(box, label, None, key, make_cb(key))

        self._refresh_inteligencia_visibility()
        return box

    def _refresh_inteligencia_visibility(self):
        """Show/hide the AI controls box based on ``ai_enabled`` config.

        Also disables the ``fish_audio`` TTS provider entry when AI is off.
        """
        enabled = self.cfg.get("ai_enabled", True)
        if hasattr(self, "_ai_controls_box"):
            self._ai_controls_box.set_visible(enabled)
        if hasattr(self, "_tts_provider_combo"):
            store = self._tts_provider_combo.get_model()
            for row in store:
                if row[0] == "fish_audio":
                    row[2] = enabled
                    break

    # ── Tab: Automation ─────────────────────────────────────────────────

    def _build_automacao(self):
        """Build the Automation / Accessibility tab content.

        Includes: model-defaults toggle, screen-reading timer (with
        random/exact modes and interval spinners), desktop audio timer,
        random speech timer, and a button to open the speech timer setup.
        """
        box = self._box()

        def _defs(state):
            self.cfg["accessibility_use_model_defaults"] = state
            self._save()
            self.parent._start_all_timers()

        self._switch_row(
            box,
            self._("menu_model_defaults"),
            self._("settings_model_defaults_desc"),
            "accessibility_use_model_defaults",
            _defs,
        )

        self._sep(box)
        self._section(box, self._("settings_screen_reading_section"))
        self._desc(box, self._("settings_screen_reading_desc"))

        def _screen(state):
            self.cfg["accessibility_enabled"] = state
            self._save()
            self.parent._start_all_timers()

        self._switch_row(
            box,
            self._("menu_screen_reading"),
            self._("settings_screen_enable_desc"),
            "accessibility_enabled",
            _screen,
        )

        def _screen_mode(mode):
            self.cfg["accessibility_mode"] = mode
            self._save()
            self.parent._start_all_timers()

        self._combo_row(
            box,
            self._("settings_mic_mode"),
            self._("settings_screen_mode_desc"),
            [("aleatorio", self._("menu_random")), ("exato", self._("menu_exact"))],
            lambda: self.cfg.get("accessibility_mode", "aleatorio"),
            _screen_mode,
        )

        self._spin_row(
            box,
            self._("settings_spin_min_label"),
            self._("settings_spin_min_desc"),
            "accessibility_min_interval",
            5,
            300,
            5,
        )
        self._spin_row(
            box,
            self._("settings_spin_max_label"),
            self._("settings_spin_max_desc"),
            "accessibility_max_interval",
            10,
            300,
            5,
        )
        self._spin_row(
            box,
            self._("settings_spin_exact_label"),
            self._("settings_spin_exact_desc"),
            "accessibility_interval",
            5,
            300,
            5,
        )

        self._sep(box)
        self._section(box, self._("settings_audio_section"))
        self._desc(box, self._("settings_audio_desc"))

        def _audio(state):
            self.cfg["accessibility_audio_enabled"] = state
            self._save()
            self.parent._start_all_timers()

        self._switch_row(
            box,
            self._("menu_desktop_audio"),
            self._("settings_audio_enable_desc"),
            "accessibility_audio_enabled",
            _audio,
        )

        def _audio_mode(mode):
            self.cfg["accessibility_audio_mode"] = mode
            self._save()
            self.parent._start_all_timers()

        self._combo_row(
            box,
            self._("settings_mic_mode"),
            self._("settings_audio_mode_desc"),
            [("aleatorio", self._("menu_random")), ("exato", self._("menu_exact"))],
            lambda: self.cfg.get("accessibility_audio_mode", "aleatorio"),
            _audio_mode,
        )

        self._spin_row(
            box,
            self._("settings_spin_min_label"),
            self._("settings_spin_audio_min_desc"),
            "accessibility_audio_min_interval",
            5,
            120,
            5,
        )
        self._spin_row(
            box,
            self._("settings_spin_max_label"),
            self._("settings_spin_audio_max_desc"),
            "accessibility_audio_max_interval",
            10,
            120,
            5,
        )
        self._spin_row(
            box,
            self._("settings_spin_exact_label"),
            self._("settings_spin_audio_exact_desc"),
            "accessibility_audio_interval",
            5,
            120,
            5,
        )

        self._sep(box)
        self._section(box, self._("settings_speech_section"))
        self._desc(box, self._("settings_speech_desc"))

        def _speech(state):
            self.cfg["accessibility_speech_enabled"] = state
            self._save()
            self.parent._start_all_timers()

        self._switch_row(
            box,
            self._("menu_random_speech"),
            self._("settings_speech_enable_desc"),
            "accessibility_speech_enabled",
            _speech,
        )

        def _speech_mode(mode):
            self.cfg["speech_mode"] = mode
            self._save()
            self.parent._start_all_timers()

        self._combo_row(
            box,
            self._("settings_mic_mode"),
            self._("settings_speech_mode_desc"),
            [("aleatorio", self._("menu_random")), ("exato", self._("menu_exact"))],
            lambda: self.cfg.get("speech_mode", "aleatorio"),
            _speech_mode,
        )

        self._spin_row(
            box,
            self._("settings_spin_min_label"),
            self._("settings_spin_speech_min_desc"),
            "speech_min_interval",
            5,
            600,
            5,
        )
        self._spin_row(
            box,
            self._("settings_spin_max_label"),
            self._("settings_spin_speech_max_desc"),
            "speech_max_interval",
            10,
            600,
            5,
        )
        self._spin_row(
            box,
            self._("settings_spin_exact_label"),
            self._("settings_spin_speech_exact_desc"),
            "speech_exact_interval",
            5,
            600,
            5,
        )

        self._sep(box)
        self._section(box, self._("settings_speak_section"))
        self._desc(box, self._("settings_speak_desc"))

        self._btn_row(
            box,
            self._("settings_speech_timer"),
            self._("settings_open_timer"),
            self._("settings_speech_timer_desc"),
            lambda *a: self.parent._setup_speech_timer(),
        )

        return box

    # ── Tab: About ──────────────────────────────────────────────────────

    def _build_sobre(self):
        """Build the About tab content.

        Shows the app name, creator credits, technology stack, and license
        / credits text.
        """
        box = self._box()

        lbl = Gtk.Label()
        lbl.set_markup("<big><b>Mate Helper</b></big>")
        lbl.set_halign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)

        lbl2 = Gtk.Label(label=self._("settings_about_subtitle"))
        lbl2.set_halign(Gtk.Align.START)
        lbl2.get_style_context().add_class("dim-label")
        box.pack_start(lbl2, False, False, 0)

        self._sep(box)

        self._section(box, self._("settings_about_section"))
        for label, value in [
            (self._("settings_created_by"), "Nina"),
            (self._("settings_original_char"), "Kasane Teto (Utau)"),
            (
                self._("settings_technologies"),
                "Python, GTK3, Groq, Gemini, HuggingFace, Ollama",
            ),
        ]:
            hb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            l = Gtk.Label(label=label)
            l.set_halign(Gtk.Align.START)
            l.set_xalign(0.0)
            l.set_size_request(160, -1)
            v = Gtk.Label(label=value)
            v.set_halign(Gtk.Align.START)
            v.set_xalign(0.0)
            v.get_style_context().add_class("dim-label")
            hb.pack_start(l, False, False, 0)
            hb.pack_start(v, False, False, 0)
            box.pack_start(hb, False, False, 0)

        self._sep(box)
        self._section(box, self._("settings_credits_section"))
        lbl = Gtk.Label(label=self._("settings_credits_text"))
        lbl.set_line_wrap(True)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_xalign(0.0)
        lbl.get_style_context().add_class("dim-label")
        box.pack_start(lbl, False, False, 0)

        return box
