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

from .world import ASSETS, floor_y, paint_by_height, point_camera

SHOTS = (3.2, 2.4, 2.6, 2.8)          # seconds per shot
FADE = 0.35
NIGHT = (16, 20, 44)


def _ease(t):
    return t * t * (3 - 2 * t)


def _lerp(a, b, k):
    return a + (b - a) * k


class Intro:
    def __init__(self, roof, count, end_pos, end_target):
        fx0, fy0, fx1, fy1 = self.fp = roof.fp
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
    @staticmethod
    def _night_tint(holder):
        """Re-colour Kenney's bright nature palette for a moonlit night: deep green needles, dark bark,
        blue-grey rock."""
        from panda3d.core import LColor
        for mat in holder.findAllMaterials():
            name = mat.getName().lower()
            if 'leaf' in name or 'grass' in name:
                mat.setBaseColor(LColor(0.09, 0.22, 0.17, 1))
            elif 'wood' in name or 'bark' in name:
                mat.setBaseColor(LColor(0.20, 0.13, 0.10, 1))
            else:
                mat.setBaseColor(LColor(0.30, 0.33, 0.45, 1))

    def _world(self):
        """Meadow, pine forest, rocky mountains (Kenney Nature Kit, CC0), moon, clouds, fog and the tower."""
        from panda3d.core import Fog
        from .floor import prop
        rng = random.Random(4)
        Sky(parent=self.root, texture='textures/night_sky')
        land = Entity(parent=self.root)
        fog = Fog('night mist')
        fog.setColor(0.09, 0.11, 0.2)
        fog.setExpDensity(0.0065)
        land.setFog(fog)
        b, cx, cz = self.bottom, self.cx, self.cz
        Entity(parent=land, model='plane', position=(cx, b, cz - 40), scale=(500, 1, 500),
               color=color.rgb(46, 74, 52))                                      # meadow
        Entity(parent=land, model='plane', position=(cx + 5, b + 0.02, cz - 70), scale=(3.4, 1, 130),
               rotation_y=-7, color=color.rgb(96, 74, 56))                       # dirt path to the tower
        h = self.top - b
        if (ASSETS / 'models' / 'tower.glb').exists():                          # modelled in Blender
            prop(self.root, 'tower', Vec3(cx, b, cz), 0, 1)                      # (tools/blender_tower.py)
        else:
            Entity(parent=land, model='cube', position=(cx, b + h / 2, cz), scale=(self.w, h, self.d),
                   texture='textures/facade', texture_scale=(self.w / 2.5, h / 2.5))
        fx0, fy0 = self.fp[0], self.fp[1]                                        # stair housing, back corner
        Entity(parent=land, model='cube', position=(fx0 + 1.0, self.top + 1.15, -(fy0 + 0.2)), scale=(2.0, 2.3, 1.8),
               color=color.rgb(64, 66, 78))
        door = Entity(parent=land, model='cube', position=(fx0 + 1.0, self.top + 0.85, -(fy0 + 0.2) - 0.91),
                      scale=(0.7, 1.3, 0.04), color=color.rgb(255, 196, 120))
        door.setLightOff()
        templates = []                                                           # Hunyuan3D peaks, painted once
        for name in ('mountain_a', 'mountain_b'):
            if (ASSETS / 'models' / (name + '.glb')).exists():
                t = prop(None, name, Vec3(0, -9999, 0), 0, 1)
                paint_by_height(t.children[0])
                t.enabled = False
                templates.append(t)
        for _ in range(12):                                                      # mountains on the horizon
            ang = rng.uniform(0.5, 2.65)
            dist = rng.uniform(170, 260)
            x, z = cx + math.cos(ang) * dist, cz + math.sin(ang) * dist
            if templates:
                peak = Entity(parent=land, position=(x, b - 3, z), rotation_y=rng.uniform(0, 360),
                              scale=rng.uniform(80, 130))
                src = rng.choice(templates).children[0]
                src.copyTo(peak).setPos(src.getPos())
            else:
                self._night_tint(prop(land, 'rock_tallA', Vec3(x, b - 2, z), rng.uniform(0, 360), rng.uniform(55, 95)))
        self.templates = templates
        pines = ['tree_pineTallA_detailed', 'tree_pineTallB_detailed', 'tree_pineTallC_detailed',
                 'tree_pineTallD_detailed', 'tree_pineDefaultA', 'tree_pineDefaultB', 'tree_pineRoundA',
                 'tree_pineRoundC']
        for _ in range(320):                                                     # pine forest around the meadow
            ang = rng.uniform(0, 6.283)
            dist = rng.uniform(self.w + 8, 130)
            x, z = cx + math.cos(ang) * dist, cz + math.sin(ang) * dist
            if z < cz - 6 and abs(x - cx) < 24:                                 # keep the meadow open
                continue
            self._night_tint(prop(land, rng.choice(pines), Vec3(x, b, z), rng.uniform(0, 360), rng.uniform(7, 12)))
        for _ in range(140):                                                     # grass tufts, rocks, stumps
            x, z = cx + rng.uniform(-30, 30), cz - rng.uniform(8, 125)
            kind = rng.choice(['grass', 'grass_large', 'grass_leafsLarge', 'grass', 'rock_largeA', 'stump_old',
                               'plant_bush'])
            self._night_tint(prop(land, kind, Vec3(x, b, z), rng.uniform(0, 360), rng.uniform(1.5, 3.2)))
        moon = Entity(parent=self.root, model='sphere', position=(cx - 90, self.top + 70, cz + 230), scale=16,
                      color=color.rgb(236, 236, 246))
        moon.setLightOff()
        halo = Entity(parent=self.root, model='circle', position=moon.position + Vec3(0, 0, 2), scale=46,
                      color=color.rgba(190, 200, 255, 40), billboard=True)
        halo.setLightOff()
        for _ in range(16):                                                      # soft clouds
            x, z, y = cx + rng.uniform(-110, 110), cz + rng.uniform(40, 170), self.top + rng.uniform(-20, 28)
            for j in range(3):
                c = Entity(parent=self.root, model='sphere', position=(x + j * 5 - 5, y + rng.uniform(-1, 1), z),
                           scale=(rng.uniform(9, 16), rng.uniform(3, 5), 7), color=color.rgba(150, 156, 190, 120))
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
        for e in (self.root, self.overlay, self.vignette, self.title, self.sub, self.button, self.frame, self.skip,
                  *self.templates):
            destroy(e)
