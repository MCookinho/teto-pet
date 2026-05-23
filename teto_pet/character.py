import math
import os
import glob

import cairo
import gi
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GdkPixbuf, Gdk, GLib

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "teto")


class Teto:
    WIDTH = 220
    HEIGHT = 320

    def __init__(self):
        self.blink = 0
        self.pixbuf = None
        self.alt_pixbufs = []
        self._load_images()

    def _load_images(self):
        os.makedirs(ASSETS_DIR, exist_ok=True)
        pngs = sorted(glob.glob(os.path.join(ASSETS_DIR, "*.png")))
        if not pngs:
            return

        # prefer smaller images (more likely to be suitable sprites)
        pngs.sort(key=lambda p: os.path.getsize(p))

        for path in pngs:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(path)
                if self.pixbuf is None:
                    self.pixbuf = pb
                else:
                    self.alt_pixbufs.append(pb)
            except GLib.Error:
                continue

    @property
    def has_image(self):
        return self.pixbuf is not None

    @property
    def aspect(self):
        if self.pixbuf:
            return self.pixbuf.get_width() / self.pixbuf.get_height()
        return self.WIDTH / self.HEIGHT

    def draw(self, cr, width, height):
        if self.pixbuf:
            self._draw_image(cr, width, height)
        else:
            self._draw_fallback(cr, width, height)

    def _draw_image(self, cr, width, height):
        pb = self.pixbuf
        img_w = pb.get_width()
        img_h = pb.get_height()

        scale = min(
            width / img_w,
            height / img_h,
            1.0
        )
        draw_w = int(img_w * scale)
        draw_h = int(img_h * scale)
        x = (width - draw_w) // 2
        y = (height - draw_h) // 2

        scaled = pb.scale_simple(
            draw_w, draw_h,
            GdkPixbuf.InterpType.BILINEAR,
        )

        Gdk.cairo_set_source_pixbuf(cr, scaled, x, y)
        cr.paint()

        self.blink = (self.blink + 1) % 120

    def _draw_fallback(self, cr, width, height):
        cx, cy = width / 2, height / 2
        sw = min(width / self.WIDTH, height / self.HEIGHT)

        cr.save()
        cr.translate(cx - (self.WIDTH * sw) / 2, cy - (self.HEIGHT * sw) / 2)
        cr.scale(sw, sw)

        self._draw_tails_back(cr)
        self._draw_legs(cr)
        self._draw_body(cr)
        self._draw_arms(cr)
        self._draw_head(cr)
        self._draw_hair_bangs(cr)
        self._draw_face(cr)
        self._draw_headband(cr)
        self._draw_tails_front(cr)

        cr.restore()

    def _draw_tails_back(self, cr):
        cr.save()
        HAIR = (200 / 255, 50 / 255, 60 / 255)
        HAIR_DARK = (150 / 255, 30 / 255, 40 / 255)
        for side in [-1, 1]:
            for layer, (w, col) in enumerate([(32, HAIR), (18, HAIR_DARK)]):
                cr.save()
                cr.translate(100 + side * 46, 110)
                cr.move_to(0, 0)
                cr.curve_to(side * -12, 40, side * -18, 100, side * -10, 170)
                cr.curve_to(side * -5, 200, 0, 210, 0, 210)
                cr.curve_to(0, 210, side * 5, 200, side * 10, 170)
                cr.curve_to(side * 18, 100, side * 12, 40, 0, 0)
                cr.close_path()
                cr.set_source_rgb(*col)
                cr.fill()
                cr.restore()
        cr.restore()

    def _draw_legs(self, cr):
        SKIN = (252 / 255, 225 / 255, 205 / 255)
        DRESS = (50 / 255, 50 / 255, 55 / 255)
        cr.save()
        cr.translate(100, 210)
        for side in [-1, 1]:
            cr.save()
            cr.translate(side * 14, 0)
            cr.move_to(-8, 0)
            cr.curve_to(-10, 20, -6, 40, -8, 55)
            cr.line_to(8, 55)
            cr.curve_to(6, 40, 10, 20, 8, 0)
            cr.close_path()
            cr.set_source_rgb(*SKIN)
            cr.fill()
            cr.move_to(-12, 55)
            cr.line_to(12, 55)
            cr.set_source_rgb(*DRESS)
            cr.set_line_width(6)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.stroke()
            cr.restore()
        cr.restore()

    def _draw_body(self, cr):
        DRESS = (50 / 255, 50 / 255, 55 / 255)
        COLLAR = (200 / 255, 50 / 255, 60 / 255)
        cr.save()
        cr.translate(100, 130)
        cr.move_to(-30, -10)
        cr.curve_to(-40, 30, -38, 70, -30, 90)
        cr.curve_to(-15, 100, 15, 100, 30, 90)
        cr.curve_to(38, 70, 40, 30, 30, -10)
        cr.close_path()
        cr.set_source_rgb(*DRESS)
        cr.fill()

        cr.set_source_rgb(*COLLAR)
        cr.set_line_width(2.5)
        cr.move_to(-5, -8)
        cr.line_to(0, 12)
        cr.line_to(5, -8)
        cr.stroke()

        for side in [-1, 1]:
            cr.save()
            cr.translate(side * 6, 10)
            cr.arc(0, 0, 4, 0, 2 * math.pi)
            cr.set_source_rgb(*COLLAR)
            cr.fill()
            cr.restore()

        cr.move_to(-22, 25)
        cr.line_to(22, 25)
        cr.set_source_rgba(1, 1, 1, 0.15)
        cr.set_line_width(1.5)
        cr.stroke()
        cr.restore()

    def _draw_arms(self, cr):
        SKIN = (252 / 255, 225 / 255, 205 / 255)
        cr.save()
        cr.translate(100, 145)
        for side in [-1, 1]:
            cr.save()
            cr.translate(side * 32, 0)
            cr.move_to(0, -5)
            cr.curve_to(side * -10, 15, side * -8, 35, side * -3, 45)
            cr.set_source_rgb(*SKIN)
            cr.set_line_width(10)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.stroke()
            cr.restore()
        cr.restore()

    def _draw_head(self, cr):
        SKIN = (252 / 255, 225 / 255, 205 / 255)
        cr.save()
        cr.translate(100, 75)
        r = 50
        cr.arc(0, 0, r, 0, 2 * math.pi)
        cr.set_source_rgb(*SKIN)
        cr.fill()
        cr.set_source_rgb(0.88, 0.78, 0.68)
        cr.set_line_width(1.5)
        cr.stroke()
        cr.restore()

    def _draw_hair_bangs(self, cr):
        HAIR = (200 / 255, 50 / 255, 60 / 255)
        HAIR_DARK = (150 / 255, 30 / 255, 40 / 255)
        cr.save()
        cr.translate(100, 75)
        r = 50

        cr.save()
        cr.arc(0, -3, r + 2, math.pi * 1.15, math.pi * 1.85)
        cr.close_path()
        cr.set_source_rgb(*HAIR)
        cr.fill()

        for xoff, w in [(-10, 28), (10, 28), (-28, 22), (28, 22)]:
            cr.save()
            cr.translate(xoff, -6)
            cr.move_to(-w / 2, -r)
            cr.curve_to(-w / 2, -r + 15, -w / 3, -r + 30, -w / 4, -r + 45)
            cr.line_to(w / 4, -r + 45)
            cr.curve_to(w / 3, -r + 30, w / 2, -r + 15, w / 2, -r)
            cr.close_path()
            cr.set_source_rgb(*HAIR)
            cr.fill()
            cr.set_source_rgb(*HAIR_DARK)
            cr.set_line_width(1)
            cr.stroke()
            cr.restore()

        cr.restore()

    def _draw_face(self, cr):
        EYE = (200 / 255, 40 / 255, 50 / 255)
        EYE_DARK = (140 / 255, 20 / 255, 30 / 255)
        CHEEK = (240 / 255, 160 / 255, 160 / 255, 0.35)
        MOUTH = (180 / 255, 80 / 255, 80 / 255)
        cr.save()
        cr.translate(100, 75)

        is_blinking = 5 < self.blink < 10

        for side in [-1, 1]:
            ex = side * 16
            ey = -2
            cr.save()
            cr.translate(ex, ey)

            cr.arc(0, 0, 12, 0, 2 * math.pi)
            cr.set_source_rgb(1, 1, 1)
            cr.fill()

            if is_blinking:
                cr.move_to(-10, 0)
                cr.line_to(10, 0)
                cr.set_source_rgb(*EYE_DARK)
                cr.set_line_width(3)
                cr.set_line_cap(cairo.LINE_CAP_ROUND)
                cr.stroke()
            else:
                cr.arc(1, 0, 7, 0, 2 * math.pi)
                cr.set_source_rgb(*EYE)
                cr.fill()

                cr.arc(1, -2, 3.5, 0, 2 * math.pi)
                cr.set_source_rgb(*EYE_DARK)
                cr.fill()

                cr.arc(3, -4, 1.5, 0, 2 * math.pi)
                cr.set_source_rgb(1, 1, 1)
                cr.fill()

                cr.arc(-3, 2, 7, 0, 2 * math.pi)
                cr.set_source_rgba(1, 1, 1, 0.08)
                cr.fill()

            cr.restore()

        for side in [-1, 1]:
            cr.save()
            cr.translate(side * 24, 12)
            cr.arc(0, 0, 6, 0, 2 * math.pi)
            cr.set_source_rgba(*CHEEK)
            cr.fill()
            cr.restore()

        cr.save()
        cr.translate(0, 16)
        cr.arc(0, 2, 5, 0.1, math.pi - 0.1)
        cr.set_source_rgb(*MOUTH)
        cr.set_line_width(2)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.stroke()
        cr.restore()

        self.blink = (self.blink + 1) % 120

        cr.restore()

    def _draw_headband(self, cr):
        RIBBON = (30 / 255, 30 / 255, 35 / 255)
        cr.save()
        cr.translate(100, 35)

        cr.move_to(-38, 0)
        cr.line_to(38, 0)
        cr.set_source_rgb(*RIBBON)
        cr.set_line_width(6)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.stroke()

        for side in [-1, 1]:
            cr.save()
            cr.translate(side * 38, 0)
            cr.move_to(0, 0)
            cr.curve_to(side * -6, -8, side * -3, -14, 0, -18)
            cr.curve_to(side * 3, -14, side * 6, -8, 0, 0)
            cr.set_source_rgb(*RIBBON)
            cr.fill()
            cr.restore()

        cr.restore()

    def _draw_tails_front(self, cr):
        HAIR = (200 / 255, 50 / 255, 60 / 255)
        HAIR_DARK = (150 / 255, 30 / 255, 40 / 255)
        cr.save()
        cr.translate(100, 75)
        for side in [-1, 1]:
            cr.save()
            cr.translate(side * 40, 42)
            for col in [HAIR, HAIR_DARK]:
                w = 26 if col == HAIR else 14
                cr.move_to(-w / 2, 0)
                cr.curve_to(-w / 2 - side * 4, 30, -w / 2 - side * 8, 70, -w / 4 - side * 6, 120)
                cr.curve_to(0, 140, 0, 150, 0, 150)
                cr.curve_to(0, 150, w / 4 - side * 6, 140, w / 2 - side * 8, 120)
                cr.curve_to(w / 2 - side * 4, 70, w / 2, 30, w / 2, 0)
                cr.close_path()
                cr.set_source_rgb(*col)
                cr.fill()
            cr.restore()
        cr.restore()
