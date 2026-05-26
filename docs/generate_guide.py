#!/usr/bin/env python3
"""Generate a comprehensive architecture & user guide PDF for Mate Helper."""

from fpdf import FPDF
import os, textwrap

OUT = os.path.join(os.path.dirname(__file__), "model-guide.pdf")

# ── Colour palette ──────────────────────────────────────────────
C_PRIMARY = (80, 60, 140)      # deep purple  -  chapter titles
C_SECONDARY = (60, 100, 160)   # steel blue  -  section titles
C_ACCENT = (200, 80, 80)       # coral  -  highlights
C_TEXT = (30, 30, 30)          # near-black body text
C_LIGHT_BG = (245, 242, 250)   # very light purple  -  info boxes
C_CODE_BG = (240, 240, 245)    # code block background
C_WHITE = (255, 255, 255)
C_GRAY = (120, 120, 120)
C_TABLE_HDR = (80, 60, 140)
C_TABLE_ALT = (248, 245, 252)

W = 210  # A4 width
H = 297  # A4 height

# ── PDF class ───────────────────────────────────────────────────
import sys
FONT_CANDIDATES = [
    "/usr/share/fonts/TTF",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"),
]
FONT_DIR = None
for d in FONT_CANDIDATES:
    if os.path.isdir(d) and os.path.isfile(os.path.join(d, "DejaVuSans.ttf")):
        FONT_DIR = d
        break
# Try to find using platform fallback
if FONT_DIR is None:
    import subprocess
    try:
        result = subprocess.run(["fc-match", "-v", "DejaVu Sans"],
                                capture_output=True, text=True, timeout=5)
        for line in result.stdout.split("\n"):
            if "file:" in line:
                fp = line.split('"')[1] if '"' in line else ""
                if fp:
                    FONT_DIR = os.path.dirname(fp)
                    break
    except Exception:
        pass
if FONT_DIR is None:
    print("DejaVu Sans not found; install ttf-dejavu or ship the font files")
    sys.exit(1)

class GuidePDF(FPDF):
    chapter = 0
    section = ""

    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(True, 18)
        self.add_font("DejaVu", "", os.path.join(FONT_DIR, "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))
        self.add_font("DejaVu", "I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf"))
        self.add_font("DejaVu", "BI", os.path.join(FONT_DIR, "DejaVuSans-BoldOblique.ttf"))

    # ── helpers ──────────────────────────────────────────
    def _rgb(self, c):
        self.set_text_color(*c)

    def _fill(self, c):
        self.set_fill_color(*c)

    def _draw_bg(self, c=C_LIGHT_BG, x=None, y=None, w=None, h=None):
        x = x or self.l_margin
        y = y or self.get_y()
        w = w or self.w - self.l_margin - self.r_margin
        h = h or 8
        self._fill(c)
        self.rect(x, y, w, h, "F")

    def header(self):
        if self.page_no() <= 1:
            return
        self.set_font("DejaVu", "I", 7)
        self._rgb(C_GRAY)
        self.cell(0, 4, "Mate Helper  -  Architecture & User Guide", align="L")
        self.cell(0, 4, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(self.l_margin, self.get_y() + 0.5, self.w - self.r_margin, self.get_y() + 0.5)
        self.ln(4)

    def footer(self):
        pass  # handled by header

    # ── title helpers ────────────────────────────────────
    def title_page(self):
        self.add_page()
        self.ln(50)
        self.set_font("DejaVu", "B", 36)
        self._rgb(C_PRIMARY)
        self.cell(0, 14, "Mate Helper", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("DejaVu", "", 18)
        self._rgb(C_SECONDARY)
        self.cell(0, 10, "Interactive Desktop Pet with AI", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)
        self.set_font("DejaVu", "I", 13)
        self._rgb(C_GRAY)
        self.cell(0, 8, "Architecture & User Guide", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(20)
        self.set_draw_color(*C_PRIMARY)
        self.set_line_width(0.6)
        self.line(60, self.get_y(), 150, self.get_y())
        self.ln(10)
        self.set_font("DejaVu", "", 10)
        self._rgb(C_TEXT)
        self.cell(0, 6, "Animated desktop companion with AI conversations,", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, "speech-to-text, text-to-speech, accessibility features,", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 6, "Libras sign language translation, and extensible character models.", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(30)
        self.set_font("DejaVu", "", 9)
        self._rgb(C_GRAY)
        self.cell(0, 5, "English Edition", align="C", new_x="LMARGIN", new_y="NEXT")

    def toc_page(self):
        self.add_page()
        self.chapter_heading("Table of Contents", is_toc=True)
        self.ln(4)
        toc = [
            ("1", "Introduction", 3),
            ("2", "Getting Started", 4),
            ("3", "System Architecture", 6),
            ("4", "Character System", 8),
            ("5", "Artificial Intelligence", 11),
            ("6", "Speech & Audio", 14),
            ("7", "Accessibility", 17),
            ("8", "User Interface", 19),
            ("9", "Configuration Reference", 22),
            ("10", "Custom Model Creation", 24),
            ("11", "Troubleshooting", 28),
            ("A", "Configuration File Reference", 30),
            ("B", "Glossary", 31),
        ]
        for num, title, pg in toc:
            self.set_font("DejaVu", "B" if "." not in num else "", 10)
            self._rgb(C_PRIMARY if "." not in num else C_TEXT)
            dots = "." * (70 - len(num) - len(title))
            self.cell(0, 6.5, f"  {num}   {title} {dots} {pg}", new_x="LMARGIN", new_y="NEXT")

    def chapter_heading(self, title, is_toc=False):
        self.set_font("DejaVu", "B", 20 if not is_toc else 18)
        self._rgb(C_PRIMARY)
        if is_toc:
            self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
            return
        self.ln(4)
        self.cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C_PRIMARY)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(6)

    def section_heading(self, title, level=2):
        if level == 2:
            self.set_font("DejaVu", "B", 14)
            self._rgb(C_SECONDARY)
            self.ln(3)
            self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*C_SECONDARY)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y() + 1, self.l_margin + 50, self.get_y() + 1)
            self.ln(4)
        else:
            self.set_font("DejaVu", "B", 11)
            self._rgb(C_ACCENT)
            self.ln(2)
            self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def body(self, text):
        self.set_font("DejaVu", "", 9.5)
        self._rgb(C_TEXT)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def bullet(self, text, indent=5):
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font("DejaVu", "", 9.5)
        self._rgb(C_TEXT)
        self.cell(4, 5, chr(8226))
        self.multi_cell(0, 5, text)
        self.ln(0.5)

    def note_box(self, text, label="NOTE"):
        self.ln(2)
        y0 = self.get_y()
        self._fill(C_LIGHT_BG)
        x, w = self.l_margin, self.w - self.l_margin - self.r_margin
        self.set_font("DejaVu", "B", 9)
        self._rgb(C_PRIMARY)
        # calculate height needed
        self.set_font("DejaVu", "", 9)
        # rough measure
        lines = len(textwrap.wrap(text, width=80))
        h = max(12, lines * 4.5 + 4)
        self.rect(x, y0, w, h, "F")
        self.set_xy(x + 3, y0 + 2)
        self.set_font("DejaVu", "B", 9)
        self._rgb(C_PRIMARY)
        self.cell(0, 4, label, new_x="LMARGIN", new_y="NEXT")
        self.set_x(x + 3)
        self.set_font("DejaVu", "", 9)
        self._rgb(C_TEXT)
        self.multi_cell(w - 6, 4.2, text)
        self.ln(2)

    def table(self, headers, rows, col_widths=None):
        """Draw a table."""
        if col_widths is None:
            col_widths = [self.w / len(headers)] * len(headers)
        sum_w = sum(col_widths)
        avail = self.w - self.l_margin - self.r_margin
        scale = avail / sum_w
        col_widths = [cw * scale for cw in col_widths]

        # header
        self.set_font("DejaVu", "B", 8.5)
        self._fill(C_TABLE_HDR)
        self._rgb(C_WHITE)
        x0 = self.l_margin
        self.set_x(x0)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 6, f" {h}", border=0, fill=True)
        self.ln()

        # rows
        self.set_font("DejaVu", "", 8)
        for ri, row in enumerate(rows):
            if ri % 2 == 1:
                self._fill(C_TABLE_ALT)
                fill = True
                self._rgb(C_TEXT)
            else:
                fill = False
                self._rgb(C_TEXT)
            self.set_x(x0)
            max_h = 5
            for i, cell in enumerate(row):
                self.cell(col_widths[i], max_h, f" {cell}", border=0, fill=fill)
            self.ln()
        self.ln(2)


def build():
    pdf = GuidePDF()
    pdf.set_margins(16, 14, 16)

    # ── Cover & TOC ──────────────────────────────────────
    pdf.title_page()
    pdf.toc_page()

    # ══════════════════════════════════════════════════════
    # Chapter 1  -  Introduction
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("1  Introduction")

    pdf.body(
        "Mate Helper is a Linux desktop application that brings an animated, AI-powered virtual pet to your screen. "
        "The pet character walks, dances, reacts emotionally, and interacts with you through speech bubbles, "
        "a text chat window, and voice commands. It can converse using multiple AI providers, "
        "execute real computer commands, describe what is happening on your screen, transcribe desktop audio, "
        "set alarms, and speak aloud with synthetic voices."
    )
    pdf.body(
        "Designed for both utility and companionship, Mate Helper serves as a friendly desktop assistant "
        "that can help with everyday tasks while providing a charming, animated presence. "
        "It supports multiple character models with different personalities and languages, "
        "and includes accessibility features for users who benefit from screen reading and audio transcription."
    )

    pdf.section_heading("Key Features")
    pdf.bullet("Animated character with five emotional moods (normal, happy, sad, angry, dancing)")
    pdf.bullet("Multi-provider AI chat: Ollama (local), Groq Cloud, Google Gemini, HuggingFace Inference API, or offline phrase library")
    pdf.bullet("Speech-to-text via microphone (push-to-talk or continuous listening modes)")
    pdf.bullet("Text-to-speech with three providers: Fish Audio, Edge TTS, and pyttsx3")
    pdf.bullet("Automatic screen reading  -  periodic screenshots described by AI")
    pdf.bullet("Automatic desktop audio transcription  -  captures and transcribes system audio")
    pdf.bullet("Libras (Brazilian Sign Language) translation with colored sign cards in speech bubbles")
    pdf.bullet("Seven AI-executable tools: open URLs, take screenshots, capture audio, read/write files, list directories, run commands, query system info")
    pdf.bullet("Alarm clock with custom MP3 ringtones")
    pdf.bullet("Extensible character model system with built-in templates")
    pdf.bullet("Multi-language support: Portuguese, English, and Japanese UI translations")
    pdf.bullet("Push-to-talk global shortcut for hands-free voice input from any application")

    pdf.section_heading("Technology Stack")
    pdf.bullet("Python 3.10+ with GTK 3, Cairo, Pango, and Pycairo for rendering")
    pdf.bullet("Pillow for image processing and GIF animation support")
    pdf.bullet("WebRTC VAD for voice activity detection on microphone input")
    pdf.bullet("PulseAudio (parec) for audio capture; ffmpeg for audio format conversion")
    pdf.bullet("Multiple AI API integrations: Ollama REST API, Groq SDK, Google Generative AI, HuggingFace Inference API")
    pdf.bullet("Whisper (via Groq) for speech-to-text transcription")
    pdf.bullet("pynput for global keyboard shortcut listening")

    pdf.section_heading("Intended Audience")
    pdf.body(
        "This guide is intended for users who want to understand how Mate Helper works under the hood, "
        "configure it for their needs, or create custom character models. It provides architectural "
        "descriptions of each subsystem without revealing proprietary source code."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 2  -  Getting Started
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("2  Getting Started")

    pdf.section_heading("System Requirements")
    pdf.bullet("Linux operating system with X11 or Wayland display server")
    pdf.bullet("Python 3.10 or newer")
    pdf.bullet("GTK 3.0 runtime libraries with Cairo and Pango support")
    pdf.bullet("PulseAudio sound server (for microphone and desktop audio capture)")
    pdf.bullet("ffmpeg (for audio format conversion)")
    pdf.bullet("Internet connection (for cloud AI providers and TTS services); Ollama mode works offline")
    pdf.bullet("Optional: Ollama for fully local AI inference")

    pdf.section_heading("Quick Start")
    pdf.body("1. Install system dependencies: GTK 3, Cairo, Pango, PulseAudio, ffmpeg, and Python 3 development headers.")
    pdf.body("2. Install Python packages: PyGObject, Pycairo, Pillow, requests, and any desired AI provider SDKs.")
    pdf.body("3. Clone or copy the application to your system.")
    pdf.body("4. Run the application: python3 desktop_pet/main.py")
    pdf.body("5. Right-click the pet to open the context menu and configure: AI provider, language, character model, and API keys.")
    pdf.body("6. Double-click the pet to open the chat window and start conversing.")

    pdf.section_heading("First-Time Configuration")
    pdf.body(
        "On first launch, the application creates a configuration file at ~/.config/mate-helper/config.json "
        "with sensible defaults. The pet appears in the "
        "center of your screen with a default character model. From the context menu, you can:"
    )
    pdf.bullet("Select an AI provider and enter API keys (for cloud services)")
    pdf.bullet("Choose a character model and language")
    pdf.bullet("Configure microphone settings for voice input")
    pdf.bullet("Enable or disable TTS (text-to-speech)")
    pdf.bullet("Set up alarms")
    pdf.bullet("Configure accessibility automation (screen reading, audio transcription)")
    pdf.bullet("Adjust window scale and speech bubble position")

    pdf.note_box(
        "For cloud AI providers (Groq, Gemini, HuggingFace), you will need to obtain API keys from their respective "
        "websites. The Ollama provider is fully local and requires no API key. The \"Phrases\" provider "
        "works entirely offline using the character's built-in phrase library."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 3  -  System Architecture
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("3  System Architecture")

    pdf.body(
        "Mate Helper follows a modular architecture where each subsystem handles a specific concern. "
        "The main application window orchestrates all components through a timer-based event loop, "
        "signal system, and shared configuration module. The following sections describe each layer "
        "of the architecture."
    )

    pdf.section_heading("3.1  Module Overview")
    pdf.table(
        ["Module", "Responsibility"],
        [
            ("app.py", "Main window, event loop, speech queue, timer management, UI menus"),
            ("character.py", "Sprite loading, mood management, frame animation, Cairo rendering"),
            ("ai.py", "AI provider abstraction, API calls, transcription, Ollama lifecycle"),
            ("chat.py", "Chat window, conversation history, tool execution, mood detection"),
            ("config.py", "JSON config persistence, defaults, migrations, validation"),
            ("tools.py", "Screenshot, audio capture, file operations, command execution"),
            ("tts.py", "Text-to-speech provider abstraction, audio playback"),
            ("libras.py", "Libras phrase dictionary, grammar rules, translation engine"),
            ("log.py", "Timestamped logging to stderr"),
            ("models/", "Model proxy, model discovery, character definitions and strings"),
        ],
        [45, 110]
    )

    pdf.section_heading("3.2  Event Loop and Scheduling")
    pdf.body(
        "The main window runs several concurrent timing mechanisms. A GTK timeout (125 ms) drives the "
        "character animation loop. Additional timers manage periodic tasks such as random speech, "
        "screen reading, audio transcription, alarm checking, and continuous microphone listening. "
        "Each timer runs on the GTK main loop thread for UI updates, while heavy operations "
        "(AI queries, audio capture, file I/O) execute in separate daemon threads to keep the "
        "interface responsive."
    )

    pdf.section_heading("3.3  Configuration Subsystem")
    pdf.body(
        "All user settings are stored in a single JSON file at ~/.config/mate-helper/config.json. "
        "The configuration module provides load and save functions that merge saved settings with "
        "a comprehensive set of defaults. On load, the system validates provider names and bubble "
        "side settings against allowed values, and applies automatic migrations for older config "
        "formats. Settings are accessible from every module via the config module's dictionary."
    )

    pdf.note_box(
        "Changes made through the context menu are saved immediately to the config file. "
        "The application does not require a restart for most configuration changes  - "
        "character model and language changes take effect on the next interaction."
    )

    pdf.section_heading("3.4  Data Flow Overview")
    pdf.body(
        "User interactions flow through the application as follows:"
    )
    pdf.body(
        "Mouse events (drag, double-click, right-click) are handled by the main window. "
        "Double-clicking opens the chat window. Right-clicking shows a context menu for configuration. "
        "Text entered in the chat window first passes through a keyword-based tool detection engine. "
        "If a tool command is recognized (e.g., \"take a screenshot\"), it is executed immediately "
        "and the result may be sent to the AI for natural-language commentary. "
        "If no tool matches, the message is sent directly to the configured AI provider. "
        "AI responses are displayed as speech bubbles and optionally spoken via TTS."
    )
    pdf.body(
        "Periodic accessibility tasks follow a separate flow: a timer captures a screenshot or "
        "audio clip, sends it to the AI for description or commentary, and displays the result "
        "as a speech bubble. The Libras translation system intercepts all speech bubble text "
        "when enabled, converting it to written Libras gloss notation before display."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 4  -  Character System
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("4  Character System")

    pdf.body(
        "The character system is responsible for loading, animating, and rendering the pet on screen. "
        "It supports multiple character models, each with their own visual appearance, personality, "
        "voice configuration, and language."
    )

    pdf.section_heading("4.1  Rendering Pipeline")
    pdf.body(
        "Characters are rendered on a GTK DrawingArea using Cairo graphics. The rendering pipeline "
        "processes each frame through these stages:"
    )
    pdf.bullet("The canvas is cleared with a fully transparent background (RGBA 0,0,0,0).")
    pdf.bullet("The character's current mood and animation frame determine which sprite to draw.")
    pdf.bullet("Sprites are scaled by the configured window scale factor (2x to 6x) for crisp pixel-art rendering.")
    pdf.bullet("If the character is speaking, the \"speaking\" variant of the current mood sprite is used.")
    pdf.bullet("The speech bubble is drawn on top of or beside the character, with auto-positioning logic.")
    pdf.bullet("A Pango text layout engine renders speech text with word-wrap and custom fonts.")
    pdf.bullet("When Libras mode is active, colored sign cards are drawn below the speech text.")

    pdf.section_heading("4.2  Moods and Animation")
    pdf.body(
        "Characters have five emotional moods, each with its own sprite set:"
    )
    pdf.table(
        ["Mood", "Description", "Trigger"],
        [
            ("Normal", "Idle/neutral state", "Default state; after any temporary mood expires"),
            ("Happy", "Positive, cheerful", "Praise, compliments, positive chat interactions"),
            ("Sad", "Down or upset", "Insults, negative language, anger from user"),
            ("Angry", "Frustrated or annoyed", "Strong negative language or hostility"),
            ("Dancing", "Celebratory animation", "Alarm ringing, special events"),
        ],
        [30, 55, 70]
    )
    pdf.body(
        "Each mood sprite can have two variants: a static/idle version and a \"speaking\" version "
        "(with an open mouth or altered expression). The system automatically switches to the "
        "speaking variant when the pet is showing a speech bubble."
    )

    pdf.section_heading("4.3  Sprite Formats")
    pdf.body(
        "Two sprite formats are supported:"
    )
    pdf.bullet(
        "Static PNG sprite sheets: A single PNG image containing all animation frames arranged "
        "horizontally. The system detects individual frame boundaries by scanning for alpha-channel "
        "transitions in the image. Each frame is assumed to be 32 pixels wide by default."
    )
    pdf.bullet(
        "Animated GIFs: The system uses Pillow to extract individual frames from GIF files along "
        "with their per-frame delay values. Frames are assembled into a horizontal strip internally "
        "and animated using the GIF's timing information."
    )
    pdf.body(
        "Sprites are stored in a sprites/ subdirectory within each model's folder. Each mood "
        "requires a separate file (e.g., Default.png, Happy.png, Sad.png, Angry.png, Dancing.gif)."
    )

    pdf.section_heading("4.4  Built-in Characters")
    pdf.body(
        "The application ships with two character types, each available in three languages:"
    )
    pdf.table(
        ["Character", "Personality", "Languages"],
        [
            ("Kasane Teto", "Energetic, playful, caring UTAUloid vocaloid. Uses emotes, slang, and short enthusiastic replies.", "Portuguese, English, Japanese"),
            ("Computer / PC", "Direct, efficient, technical assistant. Formal and straight-to-the-point, with professional responses.", "Portuguese, English, Japanese"),
        ],
        [35, 75, 45]
    )
    pdf.body(
        "Each language variant has localized UI strings, culturally appropriate phrase libraries, "
        "and region-specific TTS voice configurations. Characters can be switched at runtime "
        "from the context menu without restarting the application."
    )

    pdf.section_heading("4.5  Language System")
    pdf.body(
        "The application supports full internationalization. Each character model includes a "
        "strings module containing translations for approximately 160 UI labels, messages, "
        "and dialog texts across Portuguese, English, and Japanese. The active language is "
        "selected from the context menu and persists across sessions. Character models are "
        "loaded based on the combination of the selected character and language."
    )

    pdf.note_box(
        "The character model system is designed for extensibility. Users can create custom "
        "characters by following the template provided in the docs/custom_model/ directory. "
        "A complete guide to custom model creation is provided in Chapter 10."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 5  -  Artificial Intelligence
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("5  Artificial Intelligence")

    pdf.body(
        "The AI subsystem provides a unified interface to multiple language model providers, "
        "enabling the pet to hold natural conversations, analyze visual content, transcribe audio, "
        "and execute real computer commands through an extensible tool framework."
    )

    pdf.section_heading("5.1  Provider Architecture")
    pdf.body(
        "All AI providers share a common interface: they receive a list of conversation messages "
        "(including system prompt, user messages, and optional image data) and return a text response. "
        "The system prompt, defined by the character model, establishes the pet's personality, "
        "speech patterns, and behavioral constraints."
    )
    pdf.body(
        "The message builder automatically injects the user's name and biography (configured in "
        "the profile settings) into the conversation context. When tool permissions are enabled, "
        "a special tool-use instruction block is appended to the system prompt, teaching the AI "
        "how to issue structured tool commands."
    )

    pdf.section_heading("5.2  Provider Details")

    pdf.section_heading("Ollama (Local Inference)", 3)
    pdf.body(
        "Ollama runs large language models entirely on the local machine, requiring no internet "
        "connection or API keys. The application automatically manages the Ollama process: it "
        "checks if Ollama is running on startup, starts it if needed (via ollama serve), and "
        "terminates it on application exit. The system selects the largest available model "
        "from the user's local Ollama library, falling back to smaller models as needed."
    )
    pdf.body(
        "This provider is ideal for users who prioritize privacy, want offline operation, "
        "or wish to avoid API usage costs. Response quality depends on the local model's "
        "capabilities and system resources."
    )

    pdf.section_heading("Groq Cloud", 3)
    pdf.body(
        "Groq provides high-speed inference through their cloud API, using custom hardware "
        "accelerators for extremely low latency. The implementation uses the Llama 3.3 70B "
        "model for text conversations and Llama 4 Scout 17B for vision tasks (screenshot "
        "analysis). Audio transcription uses Groq's Whisper large-v3-turbo endpoint."
    )
    pdf.body(
        "Groq offers a generous free tier, making it a good default choice for the 'Auto' option."
        "fallback chain."
    )

    pdf.section_heading("Google Gemini", 3)
    pdf.body(
        "The Gemini integration uses Google's Gemini 2.5 Flash model (with fallbacks to 2.0 Flash "
        "and 1.5 Flash). It supports multimodal input, including images for screenshot analysis. "
        "The system performs a DNS resolution check before each API call to verify internet "
        "connectivity and provides descriptive error messages on failure."
    )

    pdf.section_heading("HuggingFace Inference API", 3)
    pdf.body(
        "HuggingFace provides community-hosted models through their Inference API. "
        "The implementation uses the Arch Router 1.5B model, a lightweight instruction-tuned "
        "model suitable for simple conversations and tool commands."
    )

    pdf.section_heading("Offline Phrases", 3)
    pdf.body(
        "When no AI provider is configured or all cloud providers fail, the system falls back to "
        "the character model's built-in phrase library. This library contains categorized responses "
        "for common conversation scenarios (greetings, how-are-you, thanks, goodbyes, etc.) and "
        "includes a keyword-matching system that selects contextually appropriate responses."
    )

    pdf.section_heading("5.3  Auto-Fallback Chain")
    pdf.body(
        "The \"Auto\" provider mode implements a resilience chain: when a request fails with one "
        "provider (due to network errors, API limits, or authentication issues), the system "
        "automatically tries the next provider in order. The fallback order is:"
    )
    pdf.body("Groq Cloud  ->  Google Gemini  ->  HuggingFace  ->  Offline Phrases")
    pdf.body(
        "This ensures the pet always responds, even when individual cloud services are unavailable. "
        "The fallback is transparent to the user, who only sees the final response."
    )

    pdf.section_heading("5.4  Vision Support")
    pdf.body(
        "Two AI providers support image inputs for screenshot analysis: Groq (with Llama 4 Scout) "
        "and Gemini (native multimodal support). When an accessibility task triggers a screenshot "
        "capture, the image is base64-encoded and sent alongside a descriptive prompt from the "
        "character model. The AI then describes what it sees in the character's personality style."
    )

    pdf.section_heading("5.5  Tool-Augmented AI")
    pdf.body(
        "One of the system's most powerful features is its tool-augmented AI capability. "
        "The AI is instructed via its system prompt that it can issue structured commands "
        "using a TOOL: prefix. When the chat system detects this prefix in the AI's response, "
        "it intercepts the command, executes it, and optionally sends the result back to the "
        "AI for a natural-language summary."
    )
    pdf.body("The AI can execute these tool categories:")
    pdf.table(
        ["Tool", "Description", "Example"],
        [
            ("Open URL", "Opens a website in the default browser", "Open youtube.com"),
            ("Screenshot", "Captures and optionally analyzes the screen", "What's on my screen?"),
            ("Audio Capture", "Records and transcribes desktop audio", "What song is playing?"),
            ("List Files", "Shows directory contents", "What's in my Downloads?"),
            ("Read File", "Displays file contents", "Read my notes.txt"),
            ("Write File", "Creates or overwrites a file", "Save this as todo.txt"),
            ("Run Command", "Executes a bash command (with safety filters)", "Check system uptime"),
        ],
        [30, 55, 70]
    )
    pdf.body(
        "Each tool has built-in safety mechanisms: dangerous shell commands are blocked by a "
        "blacklist pattern matcher, file operations are size-limited, and all tool execution "
        "is gated by individual permission toggles in the settings."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 6  -  Speech & Audio
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("6  Speech & Audio")

    pdf.body(
        "The speech and audio subsystem provides bidirectional voice interaction: speech-to-text "
        "(STT) converts your voice into text for chat input, while text-to-speech (TTS) makes "
        "the pet speak aloud. Both systems support multiple backends with automatic fallback."
    )

    pdf.section_heading("6.1  Speech-to-Text (STT)")

    pdf.section_heading("Microphone Capture Modes", 3)
    pdf.body(
        "Two microphone input modes are available:"
    )
    pdf.bullet(
        "Push-to-Talk (Hold): Press and hold a configurable key or the microphone button in the "
        "chat window. Release to stop recording and begin transcription. This mode is ideal for "
        "controlling exactly when the microphone is active."
    )
    pdf.bullet(
        "Toggle (Continuous): Click to start recording, click again to stop (with a 5-second "
        "auto-stop timeout). The system also supports a continuous listening mode that periodically "
        "captures audio every 8 seconds, automatically detecting whether speech is present."
    )
    pdf.bullet(
        "Global Push-to-Talk: A Unix socket server enables push-to-talk from any application "
        "using a configurable global shortcut (default: Win+V)."
    )

    pdf.section_heading("Voice Activity Detection", 3)
    pdf.body(
        "To prevent noise from being sent to the transcription engine, the system employs "
        "WebRTC Voice Activity Detection (VAD). Captured audio is divided into 30-millisecond "
        "frames, and each frame is analyzed by the VAD engine. If less than 5% of frames contain "
        "speech, the audio is discarded as noise. This effectively filters out ambient sounds "
        "like fans, keyboard typing, and background music while reliably capturing single-word "
        "utterances."
    )

    pdf.section_heading("Transcription Engine", 3)
    pdf.body(
        "All transcription is handled by Groq's Whisper large-v3-turbo endpoint, which provides "
        "fast and accurate speech recognition primarily for Portuguese but supporting multiple "
        "languages. Audio is captured as 16-bit PCM at 16 kHz mono via PulseAudio, converted "
        "to WAV format, and sent to the Whisper API for transcription."
    )

    pdf.section_heading("6.2  Text-to-Speech (TTS)")

    pdf.body(
        "The TTS system makes the pet speak aloud whenever it shows a speech bubble. Three "
        "providers are available, each with different quality and infrastructure trade-offs."
    )

    pdf.table(
        ["Provider", "Quality", "Requires", "Best For"],
        [
            ("Fish Audio", "Highest", "API key, internet", "Natural voices, character-specific voices"),
            ("Edge TTS", "High", "Internet", "Free high-quality voices, multiple languages"),
            ("pyttsx3", "Low-Medium", "espeak installed", "Offline use, no API needed"),
        ],
        [30, 30, 40, 55]
    )

    pdf.section_heading("Fish Audio", 3)
    pdf.body(
        "Fish Audio provides high-quality neural TTS via cloud API. The user must obtain an API "
        "key from fish.audio and configure it through the settings menu. Character models can "
        "specify a default voice ID, and users can override it with a custom voice. "
        "Fish Audio supports realistic voice cloning and produces the most natural-sounding speech."
    )

    pdf.section_heading("Edge TTS", 3)
    pdf.body(
        "Edge TTS uses Microsoft's Edge browser TTS service to generate speech. It offers "
        "high-quality voices in many languages without requiring an API key. Each character model "
        "can configure a specific Edge TTS voice (e.g., pt-BR-FranciscaNeural for Portuguese Teto). "
        "The implementation includes a 15-second timeout to handle slow network conditions."
    )

    pdf.section_heading("pyttsx3", 3)
    pdf.body(
        "pyttsx3 provides offline TTS by wrapping espeak on Linux systems. While voice quality "
        "is lower than cloud alternatives, it works without internet access and requires no "
        "API keys or configuration. This is the ultimate fallback when cloud services are unavailable."
    )

    pdf.section_heading("Auto-Fallback and Device Selection", 3)
    pdf.body(
        "When the TTS provider is set to \"Auto\", the system tries providers in order: "
        "Fish Audio first (if an API key is configured), then Edge TTS, and finally pyttsx3. "
        "Audio playback supports PulseAudio sink selection, allowing users to choose which "
        "audio output device receives the pet's voice."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 7  -  Accessibility
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("7  Accessibility")

    pdf.body(
        "Mate Helper includes several accessibility features designed to assist users with visual "
        "or hearing impairments, as well as users who prefer multimodal interaction."
    )

    pdf.section_heading("7.1  Screen Reading Automation")
    pdf.body(
        "When enabled, the system automatically captures screenshots at configurable intervals "
        "and sends them to the AI for visual description. The AI describes what it sees in the "
        "character's personality style. This can operate in two modes:"
    )
    pdf.bullet("Exact interval: A screenshot is taken at a fixed interval (e.g., every 60 seconds).")
    pdf.bullet("Random interval: Screenshots are taken at random intervals between a configurable minimum and maximum.")
    pdf.body(
        "This feature provides ambient awareness of on-screen activity for users who may have "
        "difficulty seeing screen content, or who want the pet to comment on what they are doing."
    )

    pdf.section_heading("7.2  Desktop Audio Transcription")
    pdf.body(
        "The system can periodically capture desktop audio (system output, including music, "
        "videos, and notifications) and send it to Whisper for transcription. The transcribed "
        "text is then sent to the AI for commentary. Like screen reading, this supports both "
        "exact and random interval modes."
    )
    pdf.body(
        "Audio is captured from the PulseAudio monitor source, which records whatever audio "
        "is being played through the system's speakers. Captures are limited to 8 seconds "
        "to avoid excessive processing."
    )

    pdf.section_heading("7.3  Libras (Brazilian Sign Language) Translation")
    pdf.body(
        "The Libras translation module converts Portuguese speech bubble text into written "
        "Libras gloss notation, making the pet's speech accessible to Brazilian deaf users "
        "who read Libras. The translation system operates at three levels:"
    )
    pdf.bullet(
        "Phrase dictionary: Approximately 40 common phrases (greetings, how-are-you, thanks, "
        "goodbyes, alarm messages, name introductions) have hand-crafted Libras translations "
        "that follow proper sign language grammar."
    )
    pdf.bullet(
        "Word lookup: For phrases not in the dictionary, the system looks up individual words "
        "in a sign dictionary of approximately 20 common signs (oi, obrigado, sim, nao, etc.)."
    )
    pdf.bullet(
        "Grammar rules: As a final fallback, the system applies basic Libras grammar rules: "
        "articles and prepositions are removed, conjugated verbs are simplified to infinitive "
        "form, and negation is moved to the end of the sentence."
    )
    pdf.body(
        "When Libras mode is active, each sign in the translated text is displayed as a "
        "colored rectangular card below the speech bubble text, with an 8-color palette "
        "cycling across signs for visual distinction. Cards automatically scale to fit "
        "the available bubble width."
    )

    pdf.section_heading("7.4  Random Speech")
    pdf.body(
        "The pet periodically speaks random phrases from its character model's phrase library. "
        "This creates a more lifelike and engaging companion experience. The interval between "
        "random speeches can be configured as either a fixed interval or a random range. "
        "The phrase selection uses a keyword-matching system that considers the conversation "
        "context to pick appropriate topics."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 8  -  User Interface
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("8  User Interface")

    pdf.body(
        "The user interface consists of three main components: the floating pet window, "
        "the chat dialog, and the context menu. Each is designed to be unobtrusive while "
        "providing full access to all features."
    )

    pdf.section_heading("8.1  Main Pet Window")
    pdf.body(
        "The pet resides in a frameless, transparent GTK window that floats above other "
        "applications. The window has no title bar or borders, showing only the character "
        "sprite and speech bubble on a transparent background. Key interactions:"
    )
    pdf.bullet("Click and drag to move the pet anywhere on the screen. The position is saved to configuration.")
    pdf.bullet("Double-click to open the chat window.")
    pdf.bullet("Right-click to open the context menu with all configuration options.")
    pdf.bullet("The window can be set to always stay on top of other windows.")
    pdf.bullet("The character scale can be adjusted from 2x to 6x (default: 5x).")

    pdf.section_heading("8.2  Speech Bubbles")
    pdf.body(
        "Speech bubbles are rendered with Cairo and Pango directly on the pet window. They feature:"
    )
    pdf.bullet("Rounded rectangle background with semi-transparent white fill and subtle border.")
    pdf.bullet("Animated tail pointing toward the character, positioned on the left or right side.")
    pdf.bullet("Text positioning: auto (tail points away from screen center), left, or right.")
    pdf.bullet("Automatic text wrapping with word-wrap mode for long messages.")
    pdf.bullet("Minimum bubble width of 60 pixels; width expands to fit content up to the configured maximum.")
    pdf.bullet("Duration-based display: each speech bubble stays visible for its configured duration, then fades or clears.")

    pdf.section_heading("8.3  Chat Interface")
    pdf.body(
        "The chat window provides a full messaging interface:"
    )
    pdf.bullet("Message history displayed as bubbles, with user messages on one side and pet responses on the other.")
    pdf.bullet("Text entry field with send button for keyboard input.")
    pdf.bullet("Microphone button for push-to-talk voice input (hold or toggle modes).")
    pdf.bullet("Conversation history is saved per model to ~/.config/mate-helper/history/ and persists across sessions.")
    pdf.bullet("Clear history button to reset the conversation.")
    pdf.bullet("Emits speech signals to the main window, so chat responses appear as both text and speech bubbles.")

    pdf.section_heading("8.4  Context Menu")
    pdf.body(
        "The right-click context menu is organized into logical groups:"
    )
    pdf.table(
        ["Menu Section", "Settings"],
        [
            ("Chat", "Open or close the chat window"),
            ("Intelligence", "AI provider selection, model selection for Ollama"),
            ("Permissions", "Seven individual toggles for AI tool access"),
            ("Profile", "User name and biography (injected into AI prompts)"),
            ("Pet Model", "Character model and language selection"),
            ("Alarms", "Add, list, toggle, and delete alarms"),
            ("Audio and TTS", "TTS enable/disable, provider selection, device, Fish Audio setup"),
            ("Microphone (STT)", "Microphone enable/disable, device selection, mode (hold/toggle)"),
            ("Automation", "Screen reading and audio transcription intervals and modes, Libras toggle"),
            ("Shortcuts", "Configure push-to-talk shortcut, view global shortcut help"),
            ("Language", "UI language selection (Portuguese, English, Japanese)"),
            ("Window", "Scale adjustment, always-on-top toggle, speech bubble side"),
        ],
        [45, 110]
    )

    pdf.section_heading("8.5  Push-to-Talk Shortcut")
    pdf.body(
        "The push-to-talk feature uses a Unix socket server running in a background thread. "
        "When the configured global shortcut is pressed, the application sends a signal to "
        "the socket, which triggers microphone recording. Recording continues until the key "
        "is released (in hold mode) or until a second press or timeout (in toggle mode). "
        "The shortcut can be configured from the context menu and works globally across all applications."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 9  -  Configuration Reference
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("9  Configuration Reference")

    pdf.body(
        "This chapter documents all user-configurable settings and their effects. "
        "Settings are persisted in ~/.config/mate-helper/config.json and can be modified "
        "through the context menu or by directly editing the JSON file."
    )

    pdf.section_heading("9.1  AI Settings")
    pdf.table(
        ["Setting", "Options", "Description"],
        [
            ("AI Provider", "Auto / Ollama / Groq / Gemini / HuggingFace / Phrases", "Which AI service to use for conversations"),
            ("Ollama Model", "Any installed Ollama model name", "Specific model to use when Ollama provider is active"),
            ("Groq API Key", "String", "API key for Groq Cloud access"),
            ("Gemini API Key", "String", "API key for Google Gemini access"),
            ("HuggingFace Token", "String", "API token for HuggingFace Inference API"),
        ],
        [40, 60, 55]
    )

    pdf.section_heading("9.2  Audio Settings")
    pdf.table(
        ["Setting", "Options", "Description"],
        [
            ("TTS Enabled", "On / Off", "Enable or disable all text-to-speech output"),
            ("TTS Provider", "Auto / Fish Audio / Edge TTS / pyttsx3", "Which TTS engine to use"),
            ("TTS Device", "PulseAudio sink name", "Specific audio output device for TTS"),
            ("Fish API Key", "String", "API key for Fish Audio TTS service"),
            ("Fish Voice ID", "String (optional)", "Override the character's default Fish Audio voice"),
            ("Mic STT Enabled", "On / Off", "Enable microphone speech-to-text"),
            ("Mic Device", "PulseAudio source name", "Specific microphone device"),
            ("Mic Mode", "Hold / Toggle", "Microphone activation mode"),
            ("Mic Shortcut Key", "Key name", "Global keyboard shortcut for push-to-talk"),
        ],
        [35, 55, 65]
    )

    pdf.section_heading("9.3  Automation Settings")
    pdf.table(
        ["Setting", "Options", "Description"],
        [
            ("Screen Reading", "Off / Exact / Random", "Enable automatic screen description"),
            ("Screen Interval", "Seconds (exact) or min-max range", "How often to capture and describe the screen"),
            ("Audio Transcription", "Off / Exact / Random", "Enable automatic desktop audio transcription"),
            ("Audio Interval", "Seconds (exact) or min-max range", "How often to capture and transcribe audio"),
            ("Random Speech", "On / Off", "Enable random speech from phrase library"),
            ("Speech Interval", "Seconds (exact) or min-max range", "How often the pet speaks unprompted"),
            ("Libras Translation", "On / Off", "Enable written Libras translation in speech bubbles"),
        ],
        [40, 50, 65]
    )

    pdf.section_heading("9.4  Permissions System")
    pdf.body(
        "Seven individual permission toggles control which tools the AI can execute:"
    )
    pdf.bullet("Read files  -  allows the AI to read any text file on the system")
    pdf.bullet("List files  -  allows directory content listing")
    pdf.bullet("Write files  -  allows creating and modifying files")
    pdf.bullet("Run commands  -  allows bash command execution (with safety filters)")
    pdf.bullet("Open URLs  -  allows opening websites in the browser")
    pdf.bullet("Take screenshots  -  allows screen capture and analysis")
    pdf.bullet("Listen to audio  -  allows desktop audio capture and transcription")
    pdf.note_box(
        "For security reasons, it is recommended to only enable the permissions you need. "
        "The \"Run commands\" permission in particular should be used with caution, as it "
        "gives the AI the ability to execute arbitrary bash commands."
    )

    pdf.section_heading("9.5  Alarm System")
    pdf.body(
        "Alarms are stored as part of the configuration file. Each alarm has:"
    )
    pdf.bullet("Time: Hour and minute for the alarm to trigger")
    pdf.bullet("Name: A descriptive label shown when the alarm rings")
    pdf.bullet("Enabled: Toggle to activate or deactivate without deleting")
    pdf.bullet("Ringtone: The character model's configured MP3 ringtone file")
    pdf.body(
        "When an alarm triggers, the pet switches to dancing mode, plays the ringtone, "
        "and displays an alarm message. Alarms can be stopped by clicking the alarm in the "
        "menu, typing stop words in chat (\"para\", \"cala\", \"stop\", \"shut up\"), "
        "or the alarm auto-stops after 30 seconds."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 10  -  Custom Model Creation
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("10  Custom Model Creation")

    pdf.body(
        "One of Mate Helper's most powerful features is its extensible character model system. "
        "Anyone can create a new character by providing sprites, a personality definition, "
        "a phrase library, and UI translations. This chapter provides a complete guide to "
        "creating your own custom character model."
    )

    pdf.section_heading("10.1  Understanding the Model System")
    pdf.body(
        "Each character model is a Python package (a folder with an __init__.py file) placed "
        "in the models/ directory. The model system discovers available models by scanning "
        "for folders containing a model.py file. Models can be placed either in "
        "models/default_models/{language}/ for language-specific variants or directly in "
        "models/ for standalone custom models."
    )
    pdf.body(
        "When the application starts or the model is changed via the menu, the model proxy "
        "loads the selected model's configuration, sprites, phrases, and strings. All of these "
        "are accessed through a singleton proxy object that caches the loaded module and "
        "reloads it when the model or language changes."
    )

    pdf.section_heading("10.2  Model Directory Structure")
    pdf.body("A custom model requires the following file structure:")
    pdf.body(
        "  my_model/\n"
        "    __init__.py       (empty file, marks as Python package)\n"
        "    model.py          (identity, prompts, sprites config, TTS voices)\n"
        "    phrases.py        (fallback phrases, keyword matching, alarms)\n"
        "    strings.py        (UI translations for pt, en, jp)\n"
        "    font.ttf          (optional custom font for speech bubbles)\n"
        "    ringtone.mp3      (optional alarm ringtone)\n"
        "    sprites/\n"
        "      Default.png     (idle/normal pose)\n"
        "      DefaultSpeaking.png  (speaking variant of normal)\n"
        "      Happy.png\n"
        "      HappySpeaking.png\n"
        "      Sad.png\n"
        "      SadSpeaking.png\n"
        "      Angry.png\n"
        "      AngrySpeaking.png\n"
        "      Dancing.png or Dancing.gif  (celebration animation)"
    )

    pdf.section_heading("10.3  Sprites")
    pdf.body(
        "Sprites are 32-pixel-wide images representing the character in different moods. "
        "Each mood requires a base sprite and an optional \"speaking\" variant with the "
        "mouth open. Sprites can be:"
    )
    pdf.bullet("PNG sprite sheets: A single PNG file containing frames arranged horizontally. "
               "The system auto-detects frame boundaries by scanning alpha-channel transitions. "
               "Each frame should be 32 pixels wide.")
    pdf.bullet("Animated GIFs: Supported for the dancing mood. Pillow extracts individual frames "
               "and their timing, then renders them as an animation at 8 FPS.")
    pdf.body(
        "For pixel-art characters, a scale of 5x (160 pixels on screen) provides a crisp "
        "retro look. The scale is configurable from the context menu. Sprites should be "
        "saved with transparency for proper rendering on the transparent window background."
    )

    pdf.section_heading("10.4  Model Configuration (model.py)")
    pdf.body(
        "The model.py file defines your character's identity, personality, visual configuration, "
        "and voice settings. Key configuration fields include:"
    )
    pdf.table(
        ["Field", "Purpose", "Example"],
        [
            ("MODEL_ID", "Unique identifier for the model folder", "my_custom_pet"),
            ("PET_NAME", "Full display name shown in UI", "My Custom Pet"),
            ("PET_SHORT_NAME", "Short name used in chat", "Pet"),
            ("SPRITE_NAMES", "Maps moods to sprite filenames", "Normal -> Default, Feliz -> Happy"),
            ("FONT_NAME", "Font family for speech bubbles", "Pixelify Sans"),
            ("FONT_SIZE", "Font size in points", "13"),
            ("SYSTEM_PROMPT", "AI personality definition", "\"You are a cheerful companion...\""),
            ("TTS_VOICE", "Voice IDs for each TTS provider", "{edge_tts: pt-BR-Voice}"),
            ("RINGTONE_PATH", "Path to alarm ringtone", "ringtone.mp3"),
        ],
        [30, 60, 65]
    )

    pdf.section_heading("10.5  Personality Prompt Design")
    pdf.body(
        "The SYSTEM_PROMPT is the single most important element of a character model. "
        "It defines how the AI behaves, speaks, and interacts. Effective prompts include:"
    )
    pdf.bullet("Character identity: name, background, and role (e.g., \"You are a UTAUloid vocaloid\")")
    pdf.bullet("Speech patterns: desired tone, length, and style (e.g., \"Respond in 1-2 short sentences with emotes\")")
    pdf.bullet("Behavioral rules: constraints and preferences (e.g., \"Never introduce yourself as an AI\")")
    pdf.bullet("Language: which language to respond in (e.g., \"Always respond in Brazilian Portuguese\")")
    pdf.bullet("Examples: one or two example exchanges showing desired response style")

    pdf.section_heading("10.6  Phrase Library (phrases.py)")
    pdf.body(
        "The phrase library provides fallback responses when no AI provider is available. "
        "It consists of:"
    )
    pdf.bullet("Categorized phrases: greeting, how_are_you, return_good, return_bad, thanks, bye, "
               "name, what_can_you_do, affection, jokes, sing, food, fun, curious, "
               "thanks_sarcastic, sleepy, learn, music, and unknown categories.")
    pdf.bullet("Keyword matching: A mapping of keywords to categories, enabling context-aware "
               "response selection based on user input.")
    pdf.bullet("Special phrases: Alarm notifications, thinking prefixes, conversation continuations, "
               "and tool result messages (screenshot taken, audio captured, file saved, etc.).")
    pdf.bullet("A pick() function that returns a random phrase from a named category.")

    pdf.section_heading("10.7  UI Strings (strings.py)")
    pdf.body(
        "The strings module provides translations for approximately 160 UI labels, messages, "
        "and dialog texts. Each model ships with translations for Portuguese, English, and "
        "Japanese. Required string keys cover:"
    )
    pdf.bullet("Menu labels: All context menu item names and submenu titles")
    pdf.bullet("Dialog texts: Configuration dialog descriptions and instructions")
    pdf.bullet("Button labels: Cancel, Save, Close, Ok")
    pdf.bullet("Status messages: Notifications for model loading, audio errors, configuration changes")
    pdf.bullet("Speech keys: menu_libras, menu_fish_setup, tts_provider_*")
    pdf.body(
        "A complete list of all required string keys is available in the custom model template "
        "at docs/custom_model/strings.py, which includes both the pt and en translations "
        "as a reference."
    )

    pdf.section_heading("10.8  Testing Your Model")
    pdf.body(
        "To test a custom model:"
    )
    pdf.body("1. Copy your model folder to the desktop_pet/models/ directory.")
    pdf.body("2. Ensure your sprites are in the sprites/ subfolder with correct filenames.")
    pdf.body("3. Launch Mate Helper and select your model from the context menu (Pet Model -> your model name).")
    pdf.body("4. Test each mood by triggering different interactions (chat normally for happy, insult for sad, etc.).")
    pdf.body("5. Verify the speech bubble renders correctly with your custom font (if configured).")
    pdf.body("6. Test the AI personality by asking questions in the chat window.")
    pdf.body("7. Verify that fallback phrases work by disconnecting from the internet or disabling AI providers.")

    pdf.note_box(
        "A complete, commented custom model template is available in the docs/custom_model/ "
        "directory. Copy this folder as a starting point and modify the files to create "
        "your own character. The template includes explanatory comments for every field."
    )

    # ══════════════════════════════════════════════════════
    # Chapter 11  -  Troubleshooting
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("11  Troubleshooting")

    pdf.section_heading("11.1  Common Issues")
    pdf.table(
        ["Issue", "Likely Cause", "Solution"],
        [
            ("Pet window not appearing", "Missing GTK/Python dependencies", "Install PyGObject, Pycairo, and GTK 3 development packages"),
            ("No sprites visible", "Missing sprite files or wrong paths", "Verify sprites/ directory contains all required PNG/GIF files"),
            ("AI not responding", "Missing or invalid API key, no internet", "Configure API key in Intelligence menu, or switch to Ollama/Phrases"),
            ("Microphone not working", "Wrong device selected, PulseAudio not running", "Select correct mic source in Microphone menu, verify pactl works"),
            ("TTS silent", "Missing provider dependencies, wrong device", "Install edge-tts, check PulseAudio sink selection"),
            ("Libras not translating", "Feature not enabled", "Enable in Automation menu -> Traducao para Libras"),
            ("Alarms not ringing", "Ringtone file missing", "Verify ringtone.mp3 exists in model directory"),
            ("Ollama connection failed", "Ollama not installed or not running", "Install Ollama, start with ollama serve, or choose a different provider"),
            ("Push-to-talk not working", "pynput not installed, shortcut conflict", "Install pynput, choose a different shortcut key"),
        ],
        [45, 50, 60]
    )

    pdf.section_heading("11.2  Logs and Debugging")
    pdf.body(
        "The application outputs timestamped log messages to stderr. When running from a terminal, "
        "these messages provide visibility into what the application is doing:"
    )
    pdf.bullet("STT log entries show microphone capture status and transcribed text")
    pdf.bullet("AI provider logs show which provider is being used and any errors")
    pdf.bullet("TTS logs show which provider is active and audio playback status")
    pdf.bullet("Timer logs show periodic task execution (screen reading, audio transcription)")
    pdf.body(
        "Log messages use the format [HH:MM:SS] message. To capture logs for debugging, "
        "run the application with stderr redirected to a file:"
    )
    pdf.body("  python3 desktop_pet/main.py 2> mate-helper.log")

    pdf.section_heading("11.3  Network and API Issues")
    pdf.body(
        "Cloud AI providers and TTS services require internet access. If you experience "
        "connectivity issues:"
    )
    pdf.bullet("Switch to the Ollama provider for fully local AI inference")
    pdf.bullet("Enable the \"Phrases\" provider to use only built-in fallback phrases")
    pdf.bullet("For TTS, select pyttsx3 (offline) as the provider if available")
    pdf.bullet("Check that your API keys are entered correctly and have not expired")
    pdf.bullet("Verify that your firewall allows outbound HTTPS connections to the respective API endpoints")
    pdf.body(
        "The auto-fallback mechanism means that even if your primary provider fails, "
        "the system will try alternative providers before resorting to offline mode."
    )

    pdf.section_heading("11.4  Configuration File Recovery")
    pdf.body(
        "If the configuration file becomes corrupted, delete ~/.config/mate-helper/config.json "
        "and restart the application. A fresh configuration file with defaults will be "
        "created automatically. Note that this will erase all settings, including API keys, "
        "alarms, and profile information."
    )

    # ══════════════════════════════════════════════════════
    # Appendix A  -  Configuration File Reference
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("Appendix A  Configuration File Reference")

    pdf.body(
        "The configuration file is stored at ~/.config/mate-helper/config.json. "
        "The following table documents all configuration keys and their default values."
    )

    pdf.table(
        ["Key", "Type", "Default", "Purpose"],
        [
            ("window_x", "int", "centered", "Pet window X position"),
            ("window_y", "int", "centered", "Pet window Y position"),
            ("window_scale", "int", "5", "Character sprite scale (2-6)"),
            ("language", "str", "pt", "UI language: pt, en, jp"),
            ("active_model", "str", "kasane_teto", "Active character model ID"),
            ("provider", "str", "auto", "AI provider selection"),
            ("ai_enabled", "bool", "True", "Master AI enable/disable"),
            ("ollama_model", "str", None, "Ollama model preference"),
            ("groq_key", "str", "", "Groq Cloud API key"),
            ("gemini_key", "str", "", "Google Gemini API key"),
            ("hf_token", "str", "", "HuggingFace API token"),
            ("user_name", "str", "", "User's name for AI context"),
            ("user_bio", "str", "", "User's biography for AI context"),
            ("tool_read_file", "bool", "False", "AI read file permission"),
            ("tool_list_files", "bool", "False", "AI list files permission"),
            ("tool_write_file", "bool", "False", "AI write file permission"),
            ("tool_run_command", "bool", "False", "AI run command permission"),
            ("tool_open_url", "bool", "False", "AI open URL permission"),
            ("tool_screenshot", "bool", "False", "AI screenshot permission"),
            ("tool_listen", "bool", "False", "AI audio capture permission"),
            ("always_on_top", "bool", "True", "Window always on top"),
            ("bubble_side", "str", "auto", "Speech bubble side"),
            ("libras_enabled", "bool", "False", "Libras translation toggle"),
            ("tts_enabled", "bool", "False", "TTS enable/disable"),
            ("tts_provider", "str", "auto", "TTS provider selection"),
            ("tts_device", "str", "", "TTS audio output device"),
            ("fish_audio_key", "str", "", "Fish Audio API key"),
            ("fish_audio_voice", "str", "", "Fish Audio voice override"),
            ("alarms", "list", "[]", "List of alarm objects"),
            ("mic_stt_enabled", "bool", "False", "Microphone STT enable"),
            ("mic_stt_device", "str", "", "Microphone device"),
            ("mic_stt_mode", "str", "hold", "Mic mode: hold or toggle"),
            ("stt_shortcut_key", "str", "", "Push-to-talk shortcut key"),
        ],
        [35, 15, 30, 75]
    )

    # ══════════════════════════════════════════════════════
    # Appendix B  -  Glossary
    # ══════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_heading("Appendix B  Glossary")

    glossary = [
        ("Cairo", "A 2D graphics library used for rendering the character sprite, speech bubbles, and Libras cards on the GTK drawing area."),
        ("Edge TTS", "Microsoft's cloud-based text-to-speech service accessed through the edge-tts Python library. Provides high-quality voices without requiring an API key."),
        ("Fish Audio", "A cloud TTS service offering high-quality neural voice synthesis. Requires an API key and supports custom voice profiles."),
        ("Gloss", "In the context of Libras, a written representation of sign language using capitalized Portuguese words to represent signs (e.g., \"OLA VOCE COMO-ESTA\")."),
        ("Groq", "A cloud AI inference provider offering extremely low-latency access to Llama and Whisper models through custom hardware."),
        ("Libras", "Lingua Brasileira de Sinais  -  Brazilian Sign Language, the official sign language of Brazil."),
        ("Model", "A character definition package containing identity, sprites, personality prompt, phrases, UI strings, and TTS voice configuration."),
        ("Ollama", "A local AI inference engine that runs large language models on the user's own machine without requiring internet access."),
        ("Pango", "A text layout engine used for rendering speech bubble text with word wrapping, custom fonts, and international character support."),
        ("PulseAudio", "The Linux sound server used for capturing microphone input, desktop audio, and managing TTS audio output."),
        ("pyttsx3", "An offline text-to-speech library that wraps espeak on Linux. Provides TTS without internet access, though with lower voice quality."),
        ("STT", "Speech-to-Text  -  the process of converting spoken audio into text using automatic speech recognition (Whisper)."),
        ("TTS", "Text-to-Speech  -  the process of converting written text into spoken audio using voice synthesis."),
        ("VAD", "Voice Activity Detection  -  an algorithm that determines whether a segment of audio contains human speech, used to filter out background noise."),
        ("Whisper", "OpenAI's automatic speech recognition model, accessed via Groq's API, used for transcribing microphone and desktop audio."),
    ]
    for term, defn in glossary:
        pdf.set_font("DejaVu", "B", 9.5)
        self_val = pdf  # noqa
        pdf._rgb(C_PRIMARY)
        pdf.cell(0, 5, term, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 9)
        pdf._rgb(C_TEXT)
        pdf.set_x(pdf.l_margin + 4)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 4, 4.5, defn)
        pdf.ln(2)

    # ── Save ─────────────────────────────────────────────
    pdf.output(OUT)
    print(f"PDF generated: {OUT} ({pdf.pages_count} pages)")


if __name__ == "__main__":
    build()
