"""The lift cutscene: a full-screen 2D pixel-art elevator shown while the car climbs to the next floor.

The doors, the indicator frame, the up arrow and the button strip are sprites from Elevator Pitch (Hugimugi,
Amerigo Gazaway), cut out by tools/gm_extract.py; the floor digits and the bin sprite are made by
tools/make_elevator_sprites.py. It is laid out on a 960 x 540 canvas (``px``), scaled to the window height.

Timeline over progress k = 0..1:  fade in, doors close, the bin shudders and its lid blows off as the cat
leaps out, runs about the car, then dives back in and the lid drops on; meanwhile the car shakes, the
arrow blinks and the display changes floor; doors open on a warm corridor, fade out.
"""
import math
import random

from pathlib import Path

from panda3d.core import SamplerState
from ursina import Entity, Texture, camera, color, window

from .world import ASSETS

W, H = 960, 540
GLYPHS = {i: str(i) for i in range(10)}


def glyph(index, last):
    return 'L' if index == 0 else ('R' if last else str(index))


def _lerp(a, b, k):
    return a + (b - a) * k


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class ElevatorScreen:
    def __init__(self):
        self.root = Entity(parent=camera.ui, enabled=False)
        self.rng = random.Random(7)
        STEEL, MID, DARK, LIGHT = (126, 150, 176), (92, 114, 140), (40, 48, 72), (170, 190, 208)
        self._rect(0, 0, W, H, (20, 24, 38), 0)                                          # the building behind
        self._rect(120, 0, 720, H, STEEL, 1)                                              # the car's front wall
        for y in range(0, H, 90):                                                         # panel seams
            self._rect(120, y, 720, 3, LIGHT, 1.1)
            self._rect(120, y + 3, 720, 3, MID, 1.1)
        self._rect(120, 478, 720, 62, (66, 80, 106), 1.2)                                 # floor
        self._rect(120, 478, 720, 4, LIGHT, 1.3)
        self._rect(298, 124, 364, 392, DARK, 2)                                           # door frame
        self.beyond = self._rect(330, 146, 288, 364, (255, 232, 176), 3)                  # what the doors open onto
        self.stripes = [self._rect(330, 146 + i * 60, 288, 8, (14, 16, 26), 3.1) for i in range(7)]   # shaft rushing past
        self.door_l = self._sprite('door_left', 330, 146, 144, 364, 4)
        self.door_r = self._sprite('door_right', 474, 146, 144, 364, 4)
        self._rect(120, 120, 178, 396, STEEL, 5)                                          # pockets the doors slide into
        self._rect(662, 120, 178, 396, STEEL, 5)
        self._rect(120, 120, 178, 4, DARK, 5.1)
        self._rect(662, 120, 178, 4, DARK, 5.1)
        self._sprite('panel', 410, 12, 140, 140, 6)                                       # indicator: arrows + floor digit
        self.arrow_up = self._sprite('arrow_up', 330, 44, 64, 64, 6.5)
        self.arrow_dim = self._sprite('arrow_up_dim', 330, 44, 64, 64, 6.4)
        self.digit = self._sprite('digit_0', 440, 40, 80, 80, 6.5)
        self.btn = [self._sprite('buttons_%d' % i, 700, 190, 36, 172, 6) for i in range(3)]
        self._rect(692, 180, 52, 192, DARK, 5.5)
        bw, bh = 26 * 4, 55 * 4                                                           # the bin, drawn as body + lid
        self.bin_xy = (W / 2 - bw / 2, 504 - bh)
        CW, CH = 73, 41                                                                   # one canvas for every cat frame
        self.cw, self.ch = CW * 4, CH * 4
        self.char = self._sprite('cat_sit_0', 0, 0, self.cw, self.ch, 6.9)                # the cat, behind the bin
        self.char.enabled = False
        self.bin_body = self._sprite('bin_body', *self.bin_xy, bw, bh, 7.2)
        self.bin_lid = self._sprite('bin_lid', *self.bin_xy, bw, bh, 7.3)
        self.cache = {}
        from PIL import Image                                                           # where the body's rim is in the sprite
        top = Image.open(str(ASSETS / 'textures' / 'elev' / 'bin_body.png')).getbbox()[1]
        self.rim = self.bin_xy[1] + top * 4
        self.fade = self._rect(0, 0, W, H, (0, 0, 0), 9, alpha=255)
        self.from_g, self.to_g = '0', '1'

    # ---- building blocks: logical pixels (top-left origin) -> camera.ui units ----
    @staticmethod
    def _pos(x, y):
        return ((x - W / 2) / H, (H / 2 - y) / H)

    def _rect(self, x, y, w, h, col, z, alpha=255):
        e = Entity(parent=self.root, model='quad', origin=(-.5, .5), position=(*self._pos(x, y), -z * 0.01),
                   scale=(w / H, h / H), color=color.rgba(*col, alpha))
        return e

    def _sprite(self, name, x, y, w, h, z):
        e = Entity(parent=self.root, model='quad', origin=(-.5, .5), position=(*self._pos(x, y), -z * 0.01),
                   scale=(w / H, h / H), texture='textures/elev/' + name)
        e.setTransparency(True)
        t = e.texture._texture
        t.setMagfilter(SamplerState.FT_nearest)
        t.setMinfilter(SamplerState.FT_nearest)
        e.px = (x, y)
        return e

    def _swap(self, e, name):
        t = self.cache.get(name)
        if t is None:
            t = Texture(Path(str(ASSETS / 'textures' / 'elev' / (name + '.png'))))
            t._texture.setMagfilter(SamplerState.FT_nearest)
            t._texture.setMinfilter(SamplerState.FT_nearest)
            self.cache[name] = t
        e.texture = t

    def _set_digit(self, g):
        self.digit.texture = 'textures/elev/digit_%s' % g
        t = self.digit.texture._texture
        t.setMagfilter(SamplerState.FT_nearest)
        t.setMinfilter(SamplerState.FT_nearest)

    # ---- the show ----
    def start(self, from_index, to_index, last):
        self.from_g, self.to_g = glyph(from_index, False), glyph(to_index, last)
        self._set_digit(self.from_g)
        self.root.enabled = True
        self.update(0.0)

    def update(self, k):
        """k in 0..1 over the whole ride."""
        close = _ease(k / 0.16)                                     # doors close: 0.00 .. 0.16
        opening = _ease((k - 0.84) / 0.12)                          # doors open:  0.84 .. 0.96
        shut = close * (1 - opening)
        moving = 0.20 < k < 0.82
        self.door_l.x = self._pos(330 - 144 * (1 - shut), 0)[0]
        self.door_r.x = self._pos(474 + 144 * (1 - shut), 0)[0]
        self.beyond.color = color.rgba(255, 232, 176, 255) if k > 0.82 or k < 0.16 else color.rgba(14, 16, 26, 255)
        for i, st in enumerate(self.stripes):                       # lights streaking past in the shaft
            st.enabled = moving or (0.16 <= k <= 0.2)
            st.y = self._pos(0, 146 + ((i * 60 + k * 2400) % 420))[1]
            st.color = color.rgba(60, 70, 96, 255)
        shake = (math.sin(k * 190) * 0.0016 + math.sin(k * 77) * 0.0012) if moving else 0.0
        self.root.x = shake                                         # the whole car trembles
        self.root.y = -abs(shake) * 0.6
        self._set_digit(self.to_g if k > 0.55 else self.from_g)
        blink = int(k * 14) % 2 == 0
        self.arrow_up.enabled = moving and blink or (0.16 < k < 0.2)
        self.arrow_dim.enabled = not self.arrow_up.enabled
        for i, b in enumerate(self.btn):                            # the pressed button glows
            b.enabled = i == (1 if 0.1 < k < 0.9 else 0)
        self._show(k)
        fade = 1 - _ease(k / 0.08) if k < 0.5 else _ease((k - 0.93) / 0.07)
        self.fade.color = color.rgba(0, 0, 0, int(255 * max(0.0, min(1.0, fade))))

    # ---- the bin and the character ----
    RUN = tuple(range(8))

    def _place(self, e, cx, bottom, w, h, dy=0.0):
        e.position = (*self._pos(cx - w / 2, bottom - h + dy), e.z)

    def _show(self, k):
        bx, by = self.bin_xy
        bw, bh = 26 * 4, 55 * 4
        t = k
        squash = 0.0
        lid_dy, lid_rot, lid_dx = 0.0, 0.0, 0.0
        char_on, cx, bottom, frame = False, 0.0, 500.0, 'char_guard_0'
        CY = 500.0
        REST = 504 - 44 - by                                        # the lid comes to rest on the floor beside the bin
        SIT_Y = self.rim + 10                                       # the cat sits on the bin's rim
        tilt = 0.0
        if 0.20 <= t < 0.26:                                        # the bin shudders, about to burst
            squash = math.sin((t - 0.20) / 0.06 * math.pi * 6) * 0.025 * ((t - 0.20) / 0.06)
        elif 0.26 <= t < 0.36:                                      # lid blown off, the cat leaps out onto the rim
            u = (t - 0.26) / 0.10
            lid_dy = REST * (u * u * (3 - 2 * u)) - 330 * math.sin(math.pi * u)             # up, then down to the floor
            lid_dx, lid_rot = 130 * u, 720 * u
            char_on, cx = True, 480
            bottom = _lerp(470, SIT_Y, _ease(u)) - 120 * math.sin(math.pi * u)
            frame = 'cat_run_r_%d' % (1 if u < 0.45 else (4 if u < 0.8 else 6)) if u < 0.9 else 'cat_sit_0'
        elif 0.36 <= t < 0.72:                                      # sits there, nodding like it is washing a paw
            u = t - 0.36
            char_on, cx, bottom = True, 480, SIT_Y
            frame = 'cat_sit_%d' % (int(u * 14) % 6)
            tilt = 3.5 * math.sin(u * 22) * (0.5 + 0.5 * math.sin(u * 5))
            lid_dx, lid_rot, lid_dy = 130, 720, REST
        elif 0.72 <= t < 0.78:                                      # hops back in, the lid is thrown back on
            u = (t - 0.72) / 0.06
            char_on = u < 0.92
            cx = 480
            bottom = _lerp(SIT_Y, 480, u * u) - 70 * math.sin(math.pi * min(1.0, u))
            frame = 'cat_run_r_%d' % (1 if u < 0.5 else 5)
            lid_dx, lid_rot = 130 * (1 - u), 720 * (1 - u)
            lid_dy = REST - (REST + 300) * u
        if 0.76 <= t < 0.82:                                        # the lid drops back on, a small bounce
            u = (t - 0.76) / 0.06
            lid_dx, lid_rot = 0.0, 0.0
            lid_dy = -300 * (1 - u) ** 2 if u < 0.7 else -14 * math.sin((u - 0.7) / 0.3 * math.pi)
            squash = 0.05 * math.sin(u * math.pi) if u > 0.6 else 0.0
        elif t >= 0.82:
            lid_dx = lid_rot = lid_dy = 0.0
        walking = False
        sq = 1 - squash
        self.bin_body.scale = (bw / H * (1 + squash * 0.6), bh / H * sq, 1)
        self.bin_body.position = (*self._pos(bx - bw * squash * 0.3, by + bh * (1 - sq)), self.bin_body.z)
        lx, ly = self._pos(bx + lid_dx - bw * squash * 0.3, by + lid_dy + bh * (1 - sq))
        self.bin_lid.position = (lx, ly, self.bin_lid.z)
        self.bin_lid.scale = (bw / H * (1 + squash * 0.6), bh / H * sq, 1)
        self.bin_lid.rotation_z = lid_rot
        self.char.enabled = char_on
        if char_on:
            self._swap(self.char, frame)
            self.char.z = -(7.6 if 0.34 <= t < 0.72 else 6.9) * 0.01        # in front of the bin only while it sits on top
            self.char.rotation_z = tilt
            self.char.position = (*self._pos(cx - self.cw / 2, bottom - self.ch), self.char.z)

    def hide(self):
        self.root.enabled = False

    def destroy(self):
        from ursina import destroy
        destroy(self.root)
