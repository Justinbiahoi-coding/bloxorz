"""The lift cutscene in 3D: the same show as before, but rendered with the game's own lit models.

A small elevator car sits far below the tower. The camera looks at its doors from inside the car with the bin
standing in front of them. Over progress k = 0..1: fade in, the doors close, the bin shudders and its lid is blown
off as the cat leaps out onto the rim, sits there nodding, hops back in, the lid drops back on, the doors open on
a bright corridor and the picture fades out; meanwhile the car trembles, the arrow blinks and the display changes
floor. Same interface as the old pixel version: start(from_index, to_index, last), update(k), hide().
"""
import json
import math
import random

from ursina import Cone, Entity, Text, Vec3, camera, color, destroy

from .cat import Cat
from .floor import BOX, box, glow, tex
from .world import ASSETS, FONT, aim_sun, move_lantern, point_camera

ORG = Vec3(0, -400, 0)                                   # where the car stands, far from everything else
BIN_K = 0.9


def glyph(index, last):
    return 'L' if index == 0 else ('R' if last else str(index))


def _lerp(a, b, k):
    return a + (b - a) * k


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class LiftScene:
    def __init__(self, sun):
        self.sun = sun
        self.active = False
        self.root = Entity(position=ORG, enabled=False)
        R = self.root
        steel, dark, warm = color.rgb(84, 98, 128), color.rgb(20, 22, 32), color.rgb(255, 224, 160)
        box(R, Vec3(0, -0.15, 0.5), (7.0, 0.3, 8.0), color.rgb(96, 100, 112), tex('steel'), texture_scale=(4, 4))   # floor
        for sx in (-1, 1):                                                                       # side walls
            box(R, Vec3(sx * 3.1, 1.7, 0.5), (0.2, 3.6, 8.0), steel, tex('steel'), texture_scale=(3, 2))
        box(R, Vec3(0, 3.55, 0.5), (6.4, 0.2, 8.0), color.rgb(110, 114, 126), tex('steel'))      # ceiling
        glow(R, Vec3(0, 3.42, 0.3), (2.6, 0.04, 1.4), color.rgb(255, 244, 214))                  # ceiling lamp
        # the door wall at z = 2.6: pieces either side of and above the opening (x +-1.0, up to 2.4)
        wall = lambda x, y, w, h: box(R, Vec3(x, y, 2.7), (w, h, 0.3), steel, tex('steel'), texture_scale=(w, h / 2))
        wall(-2.05, 1.7, 2.1, 3.6)
        wall(2.05, 1.7, 2.1, 3.6)
        wall(0, 3.0, 2.0, 1.2)
        for sx in (-1, 1):                                                                       # door frame
            box(R, Vec3(sx * 1.05, 1.2, 2.55), (0.12, 2.5, 0.2), dark)
        box(R, Vec3(0, 2.45, 2.55), (2.3, 0.12, 0.2), dark)
        self.beyond = glow(R, Vec3(0, 1.2, 3.3), (2.0, 2.4, 0.05), warm)                         # the corridor's light
        self.door_l = box(R, Vec3(-0.5, 1.2, 2.38), (1.0, 2.4, 0.1), color.rgb(255, 255, 255), tex('steel'))
        self.door_r = box(R, Vec3(0.5, 1.2, 2.38), (1.0, 2.4, 0.1), color.rgb(255, 255, 255), tex('steel'))
        for leaf, sx in ((self.door_l, 1), (self.door_r, -1)):                                   # a groove at each leaf's edge
            box(leaf, Vec3(sx * 0.45, 0, -0.55), (0.05, 0.85, 0.5), color.rgb(24, 28, 40))
        # indicator above the doors: a plate, the floor glyph, an up arrow either side
        box(R, Vec3(0, 3.0, 2.5), (1.5, 0.8, 0.1), color.rgb(24, 28, 44))
        self.digit = Text('L', parent=R, font=FONT, position=(0, 3.0, 2.43), origin=(0, 0), scale=22,
                          color=color.rgb(255, 214, 120))
        self.digit.rotation = (0, 0, 0)
        self.arrow_up = glow(R, Vec3(-1.35, 3.0, 2.45), (0.4, 0.5, 0.1), color.rgb(120, 255, 140), model=Cone(3))
        self.arrow_dim = glow(R, Vec3(-1.35, 3.0, 2.46), (0.4, 0.5, 0.1), color.rgb(40, 90, 60), model=Cone(3))
        # button strip on the right wall
        box(R, Vec3(3.0, 1.5, 1.5), (0.1, 1.6, 0.5), dark)
        self.btn = [glow(R, Vec3(2.93, 0.95 + i * 0.4, 1.5), (0.06, 0.18, 0.18), color.rgb(90, 96, 110), model='sphere')
                    for i in range(3)]
        # the bin: a body and a loose lid
        info = json.loads((ASSETS / 'models' / 'bin' / 'bin.json').read_text())
        self.bin_h = info['height'] * BIN_K
        self.bin = Entity(parent=R, position=(0, 0, 0.4))
        self.body = Entity(parent=self.bin, model='models/bin/bin_body', scale=BIN_K)
        self.lid_rest = Vec3(*[v * BIN_K for v in info['lid']])
        self.lid = Entity(parent=self.bin, model='models/bin/bin_lid', scale=BIN_K, position=self.lid_rest)
        for e in (self.body, self.lid):
            for m in e.findAllMaterials():
                m.setMetallic(0)
        self.cat = Cat(parent=R, scale=3.8)
        self.cat.root.rotation_y = 0                       # the cat faces -z, i.e. the camera
        self.cat.root.enabled = False
        self.fade = Entity(parent=camera.ui, model='quad', scale=(4, 2), color=color.rgba(0, 0, 0, 255), z=-2,
                           enabled=False)
        self.rng = random.Random(4)
        self.from_g, self.to_g = 'L', '1'

    # ---- control ----
    def start(self, from_index, to_index, last):
        self.from_g, self.to_g = glyph(from_index, False), glyph(to_index, last)
        self.digit.text = self.from_g
        self.root.enabled = True
        self.fade.enabled = True
        self.active = True
        from .world import set_exposure
        set_exposure(self.sun, 0.85, 0.9)
        self.update(0.0)

    def hide(self):
        self.active = False
        self.root.enabled = False
        self.fade.enabled = False

    def destroy(self):
        self.cat.destroy()
        destroy(self.root)
        destroy(self.fade)

    # ---- the show ----
    def update(self, k):
        t = k
        close = _ease(k / 0.16)
        opening = _ease((k - 0.84) / 0.12)
        shut = close * (1 - opening)
        moving = 0.20 < k < 0.82
        self.door_l.x = _lerp(-1.5, -0.5, shut)
        self.door_r.x = _lerp(1.5, 0.5, shut)
        self.digit.text = self.to_g if k > 0.55 else self.from_g
        blink = int(k * 14) % 2 == 0
        self.arrow_up.enabled = (moving and blink) or (0.16 < k < 0.2)
        self.arrow_dim.enabled = not self.arrow_up.enabled
        for i, b in enumerate(self.btn):
            b.color = color.rgb(255, 214, 90) if (i == 1 and 0.1 < k < 0.9) else color.rgb(90, 96, 110)
        self._act(k)
        shake = (math.sin(k * 190) * 0.012 + math.sin(k * 77) * 0.009) if moving else 0.0
        camera.position = ORG + Vec3(0.0 + shake, 2.5 + abs(shake) * 0.6, -10.8)
        point_camera(camera, ORG + Vec3(0, 1.6, 2.0))
        camera.fov = 36
        fade = 1 - _ease(k / 0.08) if k < 0.5 else _ease((k - 0.93) / 0.07)
        self.fade.color = color.rgba(0, 0, 0, int(255 * max(0.0, min(1.0, fade))))
        aim_sun(self.sun, ORG + Vec3(0, 1.4, 1.0))
        move_lantern(self.sun, ORG + Vec3(0, 1.4, 0.4))

    def _act(self, t):
        h = self.bin_h
        spot = Vec3(1.7, 0.0, -0.3)                                # where the cat sits, on the floor beside the bin
        lid_floor = Vec3(-2.0, 0.18, -0.5)                         # the lid lands on the other side
        squash = 0.0
        lid_pos, lid_rot = Vec3(self.lid_rest), Vec3(0, 0, 0)
        cat_on, cat_pos, frame, cat_kind, yaw = False, Vec3(0, 0, 0), 0, 'sit', 20
        pitch = 0.0
        inside = Vec3(0, 0.7, 0)
        if 0.20 <= t < 0.26:                                       # the bin shudders, about to burst
            u = (t - 0.20) / 0.06
            squash = math.sin(u * math.pi * 6) * 0.025 * u
        elif 0.26 <= t < 0.37:                                     # the lid goes, the cat leaps out over the rim
            u = (t - 0.26) / 0.11
            lid_pos = self.lid_rest + (lid_floor - self.lid_rest) * (u * u * (3 - 2 * u)) + Vec3(0, 3.6 * math.sin(math.pi * u), 0)
            lid_rot = Vec3(0, 0, -720 * u)
            cat_on = True
            e = _ease(u)
            cat_pos = Vec3(_lerp(inside.x, spot.x, e), _lerp(inside.y, spot.y, e) + 2.0 * math.sin(math.pi * u), _lerp(inside.z, spot.z, e))
            cat_kind, frame, yaw = 'run', (1 if u < 0.45 else (4 if u < 0.8 else 6)), 270
        elif 0.37 <= t < 0.71:                                     # sitting beside the bin, nodding like it is washing a paw
            u = t - 0.37
            cat_on, cat_pos = True, spot
            frame = int(u * 14)
            pitch = 6 * math.sin(u * 22) * (0.5 + 0.5 * math.sin(u * 5))
            lid_pos, lid_rot = lid_floor, Vec3(0, 0, -720)
        elif 0.71 <= t < 0.78:                                     # hops back in, the lid is thrown back up
            u = (t - 0.71) / 0.07
            cat_on = u < 0.93
            e = u * u
            cat_pos = Vec3(_lerp(spot.x, inside.x, e), _lerp(spot.y, inside.y, e) + 2.0 * math.sin(math.pi * min(1.0, u)), _lerp(spot.z, inside.z, e))
            cat_kind, frame, yaw = 'run', (1 if u < 0.5 else 5), 90
            lid_pos = lid_floor + (self.lid_rest + Vec3(0, 3.2, 0) - lid_floor) * u
            lid_rot = Vec3(0, 0, -720 * (1 - u))
        if 0.76 <= t < 0.82:                                       # the lid drops back on, a small bounce
            u = (t - 0.76) / 0.06
            lid_pos = self.lid_rest + Vec3(0, 3.2 * (1 - u) ** 2 if u < 0.7 else 0.12 * math.sin((u - 0.7) / 0.3 * math.pi), 0)
            lid_rot = Vec3(0, 0, 0)
            squash = 0.05 * math.sin(u * math.pi) if u > 0.6 else 0.0
        elif t >= 0.82:
            lid_pos, lid_rot = Vec3(self.lid_rest), Vec3(0, 0, 0)
        self.body.scale = Vec3(BIN_K * (1 + squash * 0.6), BIN_K * (1 - squash), BIN_K * (1 + squash * 0.6))
        self.lid.position = lid_pos + Vec3(0, -h * squash, 0)
        self.lid.rotation = lid_rot
        self.cat.root.enabled = cat_on
        if cat_on:
            self.cat.root.position = self.bin.position + cat_pos
            self.cat.root.rotation = (pitch, yaw, 0)
            self.cat.show('Run_F' if cat_kind == 'run' else 'Pet_sit', frame)
