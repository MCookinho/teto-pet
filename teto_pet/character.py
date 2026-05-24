import os
from enum import Enum

import cairo
import gi
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GdkPixbuf, Gdk, GLib

from teto_pet.models import model

ASSETS_DIR = model.SPRITES_DIR
FPS = 8
FRAME_MS = 1000 // FPS


class Mood(Enum):
    NORMAL = "Normal"
    FELIZ = "Feliz"
    TRISTE = "Triste"
    RAIVA = "Raiva"


MOOD_ORDER = [Mood.NORMAL, Mood.FELIZ, Mood.TRISTE, Mood.RAIVA]


class Teto:
    def __init__(self):
        self.mood = Mood.NORMAL
        self.is_talking = False
        self.frame = 0
        self.num_frames = 1
        self.frames = {}
        self._load_sheets()

    def _load_sheets(self):
        names = model.SPRITE_NAMES
        os.makedirs(ASSETS_DIR, exist_ok=True)
        for mood in MOOD_ORDER:
            pair = {}
            base = names.get(mood.value, mood.value)
            for variant in ("", "Falando"):
                suffix = variant.replace("Falando", "Speaking")
                fname = f"{base}{suffix}.png"
                path = os.path.join(ASSETS_DIR, fname)
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file(path)
                    pair[variant or "normal"] = pb
                except GLib.Error:
                    continue
            if pair:
                self.frames[mood] = pair

        if self.frames:
            sample = next(iter(next(iter(self.frames.values())).values()))
            self.num_frames = self._count_frames(sample)

    def _count_frames(self, pb):
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

    def _get_frame_pixbuf(self, sheet, frame_idx):
        sw = sheet.get_width()
        fw = sw // self.num_frames
        return sheet.new_subpixbuf(
            frame_idx * fw, 0, fw, sheet.get_height()
        )

    @property
    def has_sprite(self):
        return bool(self.frames)

    def reload_sprites(self):
        self.frames = {}
        self._load_sheets()

    def set_mood(self, mood):
        if mood in self.frames:
            self.mood = mood

    def set_talking(self, talking):
        self.is_talking = talking

    def tick(self):
        self.frame = (self.frame + 1) % self.num_frames

    def draw(self, cr, width, height, dx=None, dy=None):
        pb = self._current_sheet()
        if pb is None:
            self._draw_fallback(cr, width, height)
            return

        fw = pb.get_width() // self.num_frames
        fh = pb.get_height()
        frame_pb = self._get_frame_pixbuf(pb, self.frame)

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

        scaled = frame_pb.scale_simple(
            dw, dh, GdkPixbuf.InterpType.NEAREST
        )
        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()

    def _current_sheet(self):
        if self.mood not in self.frames:
            for m in MOOD_ORDER:
                if m in self.frames:
                    self.mood = m
                    break
            else:
                return None

        key = "Falando" if self.is_talking else "normal"
        sheets = self.frames[self.mood]
        if key in sheets:
            return sheets[key]
        if "normal" in sheets:
            return sheets["normal"]
        return next(iter(sheets.values()))

    def _draw_fallback(self, cr, width, height):
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(14)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
        cr.move_to(10, 20)
        cr.show_text("coloque sprites em:")
        cr.move_to(10, 38)
        cr.show_text(f"{model.SPRITES_DIR}/ {{mood}}{{+Speaking}}.png")
