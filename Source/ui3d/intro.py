"""Opening sequence, after the camera choreography of a night-time tower game:

  1. wide shot from a meadow: pine forest, moonlit mountains, the slender tower far away; slow push in
  2. closer: the tower fills the frame
  3. low angle at the foot of the tower, looking up its corner into the stars
  4. high corner shot above the roof with the moon behind; the title and an "Enter Building" prompt

Shots are joined by short fades to black. Any key skips to the title; Enter (or any key) at the title
goes into the game. Everything is built from primitives and code-drawn textures.
"""
import math
import random

from ursina import Cone, Entity, Sky, Text, Vec3, camera, color, destroy, window

from .world import floor_y, point_camera

SHOTS = (3.2, 2.4, 2.6, 2.8)          # seconds per shot
FADE = 0.35
NIGHT = (16, 20, 44)


def _ease(t):
    return t * t * (3 - 2 * t)


def _lerp(a, b, k):
    return a + (b - a) * k


class Intro:
    def __init__(self, roof, count, end_pos, end_target):
        fx0, fy0, fx1, fy1 = roof.fp
        self.cx, self.cz = (fx0 + fx1) / 2, -(fy0 + fy1) / 2
        self.w, self.d = fx1 - fx0 + 2.2, fy1 - fy0 + 2.2
        self.top, self.bottom = roof.base - 0.3, floor_y(count) - 3
        self.end_pos, self.end_target = end_pos, end_target
        self.root = Entity()
        self._world()
        self.overlay = Entity(parent=camera.ui, model='quad', scale=(4, 2), color=color.rgba(0, 0, 0, 0), z=-1)
        self.vignette = Entity(parent=camera.ui, model='quad', texture='textures/vignette', scale=(window.aspect_ratio, 1),
                               color=color.rgba(255, 255, 255, 220), z=-0.5)
        self.title = Text('BLOXORZ', origin=(0, 0), y=0.2, scale=6, color=color.rgba(240, 232, 220, 0))
        self.sub = Text('T O W E R', origin=(0, 0), y=0.08, scale=2.4, color=color.rgba(226, 92, 76, 0))
        self.button = Text('  Enter Building  ', origin=(0, 0), position=(0.55, -0.36), scale=1.8,
                           color=color.rgba(255, 255, 255, 0))
        self.frame = Entity(parent=camera.ui, model='quad', position=(0.55, -0.36), scale=(0.36, 0.09),
                            color=color.rgba(20, 22, 34, 0), z=0.1)
        self.skip = Text('press any key to skip', origin=(0, 0), y=-0.44, scale=1, color=color.rgba(220, 220, 230, 160))
        self.t, self.done = 0.0, False
        self.apply()

    # ---- the set ----
    def _world(self):
        rng = random.Random(4)
        r = self.root
        Sky(parent=r, texture='textures/night_sky')
        b = self.bottom
        Entity(parent=r, model='plane', position=(self.cx, b, self.cz - 40), scale=(400, 1, 400),
               color=color.rgb(30, 44, 36))                                    # meadow
        Entity(parent=r, model='plane', position=(self.cx + 6, b + 0.02, self.cz - 70), scale=(3.2, 1, 130),
               rotation_y=-8, color=color.rgb(70, 52, 40))                     # dirt path to the tower
        h = self.top - b
        Entity(parent=r, model='cube', position=(self.cx, b + h / 2, self.cz), scale=(self.w, h, self.d),
               texture='textures/facade', texture_scale=(self.w / 2, h / 2))  # the tower
        Entity(parent=r, model='cube', position=(self.cx, self.top + 0.25, self.cz), scale=(self.w + 0.6, 0.5, self.d + 0.6),
               color=color.rgb(70, 72, 84))                                    # roof slab and parapet
        Entity(parent=r, model='cube', position=(self.cx + 1, self.top + 1.4, self.cz + 1), scale=(2.4, 2.4, 2.4),
               color=color.rgb(54, 56, 66))                                    # stair housing on the roof
        for _ in range(9):                                                     # mountains on the horizon
            ang = rng.uniform(0.6, 2.6)
            dist = rng.uniform(160, 230)
            x, z = self.cx + math.cos(ang) * dist, self.cz + math.sin(ang) * dist
            hh = rng.uniform(55, 110)
            Entity(parent=r, model=Cone(5), position=(x, b, z), scale=(hh * 1.3, hh, hh * 1.3),
                   color=color.rgb(34, 42, 70), rotation_y=rng.uniform(0, 360))
            Entity(parent=r, model=Cone(5), position=(x, b + hh * 0.72, z), scale=(hh * 0.37, hh * 0.28, hh * 0.37),
                   color=color.rgb(150, 160, 190))                             # snow caps
        for _ in range(260):                                                   # pine forest around the meadow
            ang = rng.uniform(0, 6.283)
            dist = rng.uniform(self.w + 10, 120)
            x, z = self.cx + math.cos(ang) * dist, self.cz + math.sin(ang) * dist
            if z < self.cz - 6 and abs(x - self.cx) < 22:                     # keep the meadow open
                continue
            th = rng.uniform(6, 13)
            Entity(parent=r, model=Cone(6), position=(x, b + th * 0.2, z), scale=(th * 0.42, th, th * 0.42),
                   color=color.rgb(18 + rng.randint(0, 8), 34 + rng.randint(0, 10), 30))
        moon = Entity(parent=r, model='sphere', position=(self.cx - 90, self.top + 70, self.cz + 230), scale=16,
                      color=color.rgb(236, 236, 246))
        moon.setLightOff()
        halo = Entity(parent=r, model='circle', position=moon.position + Vec3(0, 0, 2), scale=46,
                      color=color.rgba(190, 200, 255, 40), billboard=True)
        halo.setLightOff()
        for _ in range(14):                                                    # low clouds
            x = self.cx + rng.uniform(-90, 90)
            z = self.cz + rng.uniform(40, 160)
            y = self.top + rng.uniform(-20, 25)
            c = Entity(parent=r, model='sphere', position=(x, y, z), scale=(rng.uniform(14, 30), 4, 8),
                       color=color.rgba(120, 128, 160, 150))
            c.setLightOff()

    # ---- the camera ----
    def _shot(self, i, k):
        cx, cz, b, top, w, d = self.cx, self.cz, self.bottom, self.top, self.w, self.d
        if i == 0:      # wide from the meadow, slow push in
            return Vec3(cx + 4, b + 1.8, _lerp(cz - 120, cz - 95, k)), Vec3(cx, b + 14, cz)
        if i == 1:      # closer: the tower fills the frame
            return Vec3(cx + 2, b + 2.2, _lerp(cz - 62, cz - 48, k)), Vec3(cx, b + 22, cz)
        if i == 2:      # foot of the tower, looking up the corner
            return (Vec3(cx + w / 2 + 3.5, b + 1.2 + 4 * k, cz - d / 2 - 3.5),
                    Vec3(cx + w / 2 - 1, _lerp(b + 30, top + 10, k), cz - d / 2 + 1))
        return (Vec3(_lerp(cx - w * 1.4, cx - w * 1.2, k), top + w * 0.95, cz - d * 1.5),   # above the roof
                Vec3(cx, top - 2, cz + 2))

    def skip_or_enter(self):
        if self.t < sum(SHOTS):
            self.t = sum(SHOTS)
        else:
            self.done = True

    def step(self, dt):
        self.t += dt
        self.apply()

    def apply(self):
        t, i = self.t, 0
        while i < len(SHOTS) - 1 and t > SHOTS[i]:
            t -= SHOTS[i]
            i += 1
        k = min(1.0, t / SHOTS[i])
        pos, target = self._shot(i, _ease(k))
        camera.position = pos
        point_camera(camera, target)
        window.color = color.rgb(*NIGHT)
        fade = 0.0                                                             # dip to black between shots
        if i > 0 and t < FADE:
            fade = 1 - t / FADE
        elif i < len(SHOTS) - 1 and SHOTS[i] - t < FADE:
            fade = 1 - (SHOTS[i] - t) / FADE
        self.overlay.color = color.rgba(0, 0, 0, int(255 * fade))
        a = 0.0 if i < 3 else min(1.0, t / 1.2)
        self.title.color = color.rgba(240, 232, 220, int(255 * a))
        self.sub.color = color.rgba(226, 92, 76, int(255 * a))
        ready = self.t >= sum(SHOTS)
        self.button.color = color.rgba(255, 255, 255, int(255 * a) if i == 3 else 0)
        self.frame.color = color.rgba(20, 22, 34, int(200 * a) if i == 3 else 0)
        self.skip.enabled = not ready and i < 3

    def destroy(self):
        for e in (self.root, self.overlay, self.vignette, self.title, self.sub, self.button, self.frame, self.skip):
            destroy(e)
