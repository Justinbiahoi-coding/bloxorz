"""Opening shot in 3D: the tower stands in a night city; the camera rises along its front from the street
to the roof at golden hour, then settles into the play view of the rooftop."""
import math
import random

from ursina import Entity, Text, Vec3, camera, color, destroy, window

from .world import floor_y

RISE_S = 6.0
NIGHT, GOLD = (14, 18, 40), (250, 196, 150)


def _ease(t):
    return t * t * (3 - 2 * t)


class Intro:
    def __init__(self, roof, count, end_pos, end_target):
        fx0, fy0, fx1, fy1 = roof.fp
        self.cx, self.cz = (fx0 + fx1) / 2, -(fy0 + fy1) / 2
        w, d = fx1 - fx0 + 2.2, fy1 - fy0 + 2.2
        self.top, self.bottom = roof.base - 0.3, floor_y(count) - 3
        h = self.top - self.bottom
        self.root = Entity()
        Entity(parent=self.root, model='cube', position=(self.cx, self.bottom + h / 2, self.cz), scale=(w, h, d),
               texture='textures/facade', texture_scale=(w / 2, h / 2))
        Entity(parent=self.root, model='plane', position=(self.cx, self.bottom, self.cz), scale=400,
               color=color.rgb(24, 26, 34))
        rng = random.Random(5)
        for _ in range(40):                                   # the city around it
            ang = rng.uniform(0, 6.283)
            r = rng.uniform(w + 6, 70)
            bw, bh = rng.uniform(4, 10), rng.uniform(8, h * 0.8)
            x, z = self.cx + r * math.cos(ang), self.cz + r * math.sin(ang)
            if z < self.cz - 4 and abs(x - self.cx) < w:      # keep the camera's line of sight clear
                continue
            Entity(parent=self.root, model='cube', position=(x, self.bottom + bh / 2, z), scale=(bw, bh, bw),
                   texture='textures/facade', texture_scale=(bw / 2, bh / 2), color=color.rgb(150, 150, 170))
        self.end_pos, self.end_target = end_pos, end_target
        self.t, self.done = 0.0, False
        self.title = Text('BLOXORZ', origin=(0, 0), y=0.3, scale=5, color=color.rgba(255, 244, 232, 0))
        self.sub = Text('T O W E R', origin=(0, 0), y=0.2, scale=2, color=color.rgba(255, 138, 91, 0))
        self.prompt = Text('Press any key', origin=(0, 0), y=-0.42, scale=1.4, color=color.rgba(255, 255, 255, 0))
        self.apply()

    def skip(self):
        if self.t < 1:
            self.t = 1.0
        else:
            self.done = True

    def step(self, dt):
        self.t = min(1.0, self.t + dt / RISE_S)
        self.apply()

    def apply(self):
        k = _ease(self.t)
        rise = min(1.0, k / 0.8)                              # 80%: up the facade, 20%: over into the roof view
        y = self.bottom + 2 + (self.top + 6 - self.bottom - 2) * rise
        pos = Vec3(self.cx, y, self.cz - 30)
        target = Vec3(self.cx, y + 4 - 4 * rise, self.cz)
        if k > 0.8:
            j = (k - 0.8) / 0.2
            pos = pos + (self.end_pos - pos) * j
            target = target + (self.end_target - target) * j
        camera.position = pos
        camera.look_at(target)
        window.color = color.rgb(*[int(a + (b - a) * rise) for a, b in zip(NIGHT, GOLD)])
        a = max(0.0, (k - 0.75) / 0.25)
        self.title.color = color.rgba(255, 244, 232, int(255 * a))
        self.sub.color = color.rgba(255, 138, 91, int(255 * a))
        self.prompt.color = color.rgba(255, 255, 255, int(255 * a) if self.t >= 1 else 0)

    def destroy(self):
        for e in (self.root, self.title, self.sub, self.prompt):
            destroy(e)
