"""The lift cutscene: a full-screen 2D pixel-art elevator shown while the car climbs to the next floor.

The doors, the indicator frame, the up arrow and the button strip are sprites from Elevator Pitch (Hugimugi,
Amerigo Gazaway), cut out by tools/gm_extract.py; the floor digits and the bin sprite are made by
tools/make_elevator_sprites.py. It is laid out on a 960 x 540 canvas (``px``), scaled to the window height.

Timeline over progress k = 0..1:  fade in, doors close, the car shakes and the arrow blinks while the display
changes floor, doors open on a warm corridor, fade out.
"""
import math
import random

from panda3d.core import SamplerState
from ursina import Entity, camera, color, window

W, H = 960, 540
GLYPHS = {i: str(i) for i in range(10)}


def glyph(index, last):
    return 'L' if index == 0 else ('R' if last else str(index))


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
        self.bin = self._sprite('bin', 424, 248, 124, 256, 7)                             # the survivor, in the car
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
        opening = _ease((k - 0.80) / 0.14)                          # doors open:  0.80 .. 0.94
        shut = close * (1 - opening)
        moving = 0.20 < k < 0.78
        self.door_l.x = self._pos(330 - 144 * (1 - shut), 0)[0]
        self.door_r.x = self._pos(474 + 144 * (1 - shut), 0)[0]
        self.beyond.color = color.rgba(255, 232, 176, 255) if k > 0.78 or k < 0.16 else color.rgba(14, 16, 26, 255)
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
        self.bin.y = self._pos(0, 248)[1] + (math.sin(k * 90) * 0.0015 if moving else 0.0)
        fade = 1 - _ease(k / 0.08) if k < 0.5 else _ease((k - 0.93) / 0.07)
        self.fade.color = color.rgba(0, 0, 0, int(255 * max(0.0, min(1.0, fade))))

    def hide(self):
        self.root.enabled = False

    def destroy(self):
        from ursina import destroy
        destroy(self.root)
