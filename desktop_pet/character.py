"""
Sprite rendering for the Mate Helper desktop pet.

Loads animated GIFs or static PNGs for each mood, renders them as
Cairo surfaces scaled to the window size, and handles frame
advancement for both GIF-based (per-frame delays) and sprite-sheet
(equal-width columns) animations.
"""

import os
from enum import Enum

import cairo
from PIL import Image

import gi
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GdkPixbuf, Gdk, GLib

from desktop_pet.models import model

ASSETS_DIR = model.SPRITES_DIR
FPS = 8
FRAME_MS = 1000 // FPS


class Mood(Enum):
    """Available character moods, each mapped to a sprite filename suffix."""
    NORMAL = "Normal"
    FELIZ = "Feliz"
    TRISTE = "Triste"
    RAIVA = "Raiva"
    DANCA = "Dança"


MOOD_ORDER = [Mood.NORMAL, Mood.FELIZ, Mood.TRISTE, Mood.RAIVA, Mood.DANCA]


class Teto:
    """Manages sprite sheets and frame animation for the desktop pet character."""

    def __init__(self):
        self.mood = Mood.NORMAL
        self.is_talking = False
        self.frame = 0
        self.num_frames = 1
        self.frames = {}            # {mood: {variant: pixbuf}}
        self._gif_frames = {}       # {(mood, variant): True} — marks GIF sources
        self._gif_delays = {}       # {(mood, variant): [ms, ...]}
        self._gif_elapsed = 0
        self._load_sheets()

    # ── GIF loading ──────────────────────────────────────────────

    def _load_gif(self, path):
        """Load a GIF, extract every frame as a GdkPixbuf, and stitch them
        into a horizontal sprite sheet.  Returns ``(sheet, delays)`` or
        ``(None, 0)`` on failure.

        ``delays`` is a list of per-frame durations (ms, minimum 50 ms).
        """
        try:
            img = Image.open(path)
        except Exception:
            return None, 0

        frames = []
        delays = []
        try:
            while True:
                f = img.copy().convert("RGBA")
                w, h = f.size
                data = f.tobytes()
                pb = GdkPixbuf.Pixbuf.new_from_bytes(
                    GLib.Bytes.new(data), GdkPixbuf.Colorspace.RGB, True, 8,
                    w, h, w * 4,
                )
                frames.append(pb)
                delays.append(max(img.info.get("duration", 100), 50))
                img.seek(img.tell() + 1)
        except EOFError:
            pass

        if not frames:
            return None, 0

        fw = frames[0].get_width()
        fh = frames[0].get_height()
        sheet = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, True, 8, fw * len(frames), fh,
        )
        sheet.fill(0)
        for i, pf in enumerate(frames):
            pf.copy_area(0, 0, fw, fh, sheet, i * fw, 0)
        return sheet, delays

    # ── Sheet loading ────────────────────────────────────────────

    def _load_sheets(self):
        """Scan ASSETS_DIR for sprite files and populate ``self.frames``.

        For each mood, looks for two variants:
          * ``{mood}.gif`` or ``{mood}.png`` (normal/idle)
          * ``{mood}Speaking.gif`` or ``{mood}Speaking.png`` (talking)

        GIFs are preferred; PNGs are used as single-frame fallbacks.
        """
        names = model.SPRITE_NAMES
        os.makedirs(ASSETS_DIR, exist_ok=True)

        for mood in MOOD_ORDER:
            pair = {}
            base = names.get(mood.value, mood.value)

            for variant in ("", "Falando"):
                suffix = variant.replace("Falando", "Speaking")
                key = variant or "normal"

                # Try GIF first.
                gif_path = os.path.join(ASSETS_DIR, f"{base}{suffix}.gif")
                if os.path.exists(gif_path):
                    sheet, delays = self._load_gif(gif_path)
                    if sheet is not None:
                        pair[key] = sheet
                        self._gif_frames[(mood, key)] = True
                        self._gif_delays[(mood, key)] = delays
                        self.num_frames = max(self.num_frames, len(delays))
                        continue

                # Fall back to static PNG.
                png_path = os.path.join(ASSETS_DIR, f"{base}{suffix}.png")
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file(png_path)
                    pair[key] = pb
                except GLib.Error:
                    continue

            if pair:
                self.frames[mood] = pair

        # If we only loaded single-frame PNGs, auto-detect how many
        # equal-width columns the first sheet contains.
        if self.frames and self.num_frames <= 1:
            sample = next(iter(next(iter(self.frames.values())).values()))
            self.num_frames = self._count_frames(sample)

    # ── Auto-frame-count via alpha scanning ──────────────────────

    def _count_frames(self, pb):
        """Heuristic: scan the first 32 rows of *pb* for non-transparent
        columns to determine how many equal-width frames are packed
        into the horizontal sprite sheet.

        This works because frames are separated by fully-transparent
        vertical gaps.
        """
        w = pb.get_width()
        stride = pb.get_rowstride()
        pixels = pb.get_pixels()

        content_starts = []
        in_content = False
        for x in range(w):
            has = False
            for y in range(32):
                if pixels[y * stride + x * 4 + 3] > 10:
                    has = True
                    break
            if has and not in_content:
                content_starts.append(x)
                in_content = True
            elif not has:
                in_content = False

        if len(content_starts) < 2:
            return 1

        spacing = content_starts[1] - content_starts[0]
        return w // spacing

    # ── Frame extraction ─────────────────────────────────────────

    def _get_frame_pixbuf(self, sheet, frame_idx):
        """Extract a single frame from a horizontal sprite sheet."""
        fw = sheet.get_width() // self.num_frames
        return sheet.new_subpixbuf(frame_idx * fw, 0, fw, sheet.get_height())

    # ── Public API ───────────────────────────────────────────────

    @property
    def has_sprite(self):
        return bool(self.frames)

    def reload_sprites(self):
        """Re-scan ASSETS_DIR and rebuild internal state."""
        self.frames = {}
        self._gif_frames = {}
        self._gif_delays = {}
        self._gif_elapsed = 0
        self.num_frames = 1
        self._load_sheets()

    def set_mood(self, mood):
        if mood in self.frames:
            self.mood = mood

    def set_talking(self, talking):
        self.is_talking = talking

    def _current_key(self):
        """Return ``(mood, variant_key)`` for the current state, falling
        back through moods if the current one has no sprites loaded.
        """
        if self.mood not in self.frames:
            for m in MOOD_ORDER:
                if m in self.frames:
                    self.mood = m
                    break
            else:
                return None, None

        key = "Falando" if self.is_talking else "normal"
        sheets = self.frames[self.mood]
        if key in sheets:
            return self.mood, key
        if "normal" in sheets:
            return self.mood, "normal"
        fallback = next(iter(sheets))
        return self.mood, fallback

    # ── Animation tick ───────────────────────────────────────────

    def tick(self):
        """Advance the animation by one frame (called periodically by the
        GTK timer).  For GIF-based sprites, uses per-frame delays;
        for sprite sheets, cycles through equally-spaced columns.
        """
        mood, key = self._current_key()
        if mood is None:
            self.frame = 0
            return

        delays = self._gif_delays.get((mood, key))
        if delays:
            self._gif_elapsed += FRAME_MS
            total = sum(delays)
            self._gif_elapsed %= total
            acc = 0
            for i, d in enumerate(delays):
                acc += d
                if self._gif_elapsed < acc:
                    self.frame = i
                    return
            self.frame = 0
        else:
            self.frame = (self.frame + 1) % self.num_frames

    # ── Drawing ──────────────────────────────────────────────────

    def draw(self, cr, width, height, dx=None, dy=None):
        """Draw the current frame onto a Cairo context, centred and
        scaled to fit the given *width* x *height* (capped at 6×).

        If no sprite is loaded, draws a fallback text message.
        """
        mood, key = self._current_key()
        if mood is None:
            self._draw_fallback(cr, width, height)
            return

        sheet = self.frames[mood][key]
        fw = sheet.get_width() // self.num_frames
        fh = sheet.get_height()
        frame_pb = self._get_frame_pixbuf(sheet, self.frame)

        scale = min(width / fw, height / fh, 6.0)
        dw = int(fw * scale)
        dh = int(fh * scale)

        if dx is None:
            x = (width - dw) // 2
        else:
            x = dx
        if dy is None:
            y = (height - dh) // 2
        else:
            y = dy

        scaled = frame_pb.scale_simple(dw, dh, GdkPixbuf.InterpType.NEAREST)
        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()

    def _draw_fallback(self, cr, width, height):
        """Fallback text overlay when no sprites are found."""
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(14)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
        cr.move_to(10, 20)
        cr.show_text("coloque sprites em:")
        cr.move_to(10, 38)
        cr.show_text(f"{model.SPRITES_DIR}/ {{mood}}{{+Speaking}}.png")
