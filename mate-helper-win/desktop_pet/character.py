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
    NORMAL = "Normal"
    FELIZ = "Feliz"
    TRISTE = "Triste"
    RAIVA = "Raiva"
    DANCA = "Dança"


MOOD_ORDER = [Mood.NORMAL, Mood.FELIZ, Mood.TRISTE, Mood.RAIVA, Mood.DANCA]


class Teto:
    def __init__(self):
        self.mood = Mood.NORMAL
        self.is_talking = False
        self.frame = 0
        self.num_frames = 1
        self.frames = {}
        self._gif_frames = {}
        self._gif_delays = {}
        self._gif_elapsed = 0
        self._load_sheets()

    def _load_gif(self, path):
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
            GdkPixbuf.Colorspace.RGB, True, 8, fw * len(frames), fh
        )
        sheet.fill(0)
        for i, pf in enumerate(frames):
            pf.copy_area(0, 0, fw, fh, sheet, i * fw, 0)
        return sheet, delays

    def _load_sheets(self):
        names = model.SPRITE_NAMES
        os.makedirs(ASSETS_DIR, exist_ok=True)
        for mood in MOOD_ORDER:
            pair = {}
            base = names.get(mood.value, mood.value)
            for variant in ("", "Falando"):
                suffix = variant.replace("Falando", "Speaking")
                key = variant or "normal"
                gif_path = os.path.join(ASSETS_DIR, f"{base}{suffix}.gif")
                if os.path.exists(gif_path):
                    sheet, delays = self._load_gif(gif_path)
                    if sheet is not None:
                        pair[key] = sheet
                        self._gif_frames[(mood, key)] = True
                        self._gif_delays[(mood, key)] = delays
                        self.num_frames = max(self.num_frames, len(delays))
                        continue
                png_path = os.path.join(ASSETS_DIR, f"{base}{suffix}.png")
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file(png_path)
                    pair[key] = pb
                except GLib.Error:
                    continue
            if pair:
                self.frames[mood] = pair

        if self.frames and self.num_frames <= 1:
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

    def tick(self):
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

    def draw(self, cr, width, height, dx=None, dy=None):
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

        scaled = frame_pb.scale_simple(
            dw, dh, GdkPixbuf.InterpType.NEAREST
        )
        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()

    def _draw_fallback(self, cr, width, height):
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(14)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
        cr.move_to(10, 20)
        cr.show_text("coloque sprites em:")
        cr.move_to(10, 38)
        cr.show_text(f"{model.SPRITES_DIR}/ {{mood}}{{+Speaking}}.png")
