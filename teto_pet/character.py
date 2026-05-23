import os
import glob
from enum import Enum

import cairo
import gi
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GdkPixbuf, Gdk

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "teto")


class Mood(Enum):
    NORMAL = "Normal"
    FELIZ = "Feliz"
    TRISTE = "Triste"
    RAIVA = "Raiva"


MOOD_ORDER = [Mood.NORMAL, Mood.FELIZ, Mood.TRISTE, Mood.RAIVA]

SPRITE_W = 128
SPRITE_H = 32


class Teto:
    def __init__(self):
        self.mood = Mood.NORMAL
        self.is_talking = False
        self.sprites = {}
        self._load_sprites()

    def _load_sprites(self):
        os.makedirs(ASSETS_DIR, exist_ok=True)
        for mood in MOOD_ORDER:
            pair = {}
            for variant in ("", "Falando"):
                fname = f"Teto{mood.value}{variant}.png"
                path = os.path.join(ASSETS_DIR, fname)
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file(path)
                    pair[variant or "normal"] = pb
                except GLib.Error:
                    pass
            if pair:
                self.sprites[mood] = pair

    @property
    def has_sprite(self):
        return bool(self.sprites)

    def set_mood(self, mood):
        if mood in self.sprites:
            self.mood = mood

    def set_talking(self, talking):
        self.is_talking = talking

    def draw(self, cr, width, height):
        pb = self._current_pixbuf()
        if pb is None:
            self._draw_fallback(cr, width, height)
            return

        img_w = pb.get_width()
        img_h = pb.get_height()

        scale = min(width / img_w, height / img_h, 4.0)
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)
        x = (width - draw_w) // 2
        y = (height - draw_h) // 2

        scaled = pb.scale_simple(
            draw_w, draw_h,
            GdkPixbuf.InterpType.NEAREST,
        )

        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()

    def _current_pixbuf(self):
        if self.mood not in self.sprites:
            for m in MOOD_ORDER:
                if m in self.sprites:
                    self.mood = m
                    break
            else:
                return None

        key = "Falando" if self.is_talking else "normal"
        sprites = self.sprites[self.mood]
        if key in sprites:
            return sprites[key]
        if "normal" in sprites:
            return sprites["normal"]
        return next(iter(sprites.values()))

    def _draw_fallback(self, cr, width, height):
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(14)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
        cr.move_to(10, 20)
        cr.show_text("coloque sprites em:")
        cr.move_to(10, 38)
        cr.show_text("assets/teto/Teto*.png")
