"""Opening cutscene: the day the city fell (bright daylight, after the Zombie Barricades trailer).

  1. ten seconds: five from high above at an angle, over burning blocks and the dead in the streets to a
     rooftop helipad; then five low on the ground, gliding in through a checkpoint gate and down the ruined street
  2. a ruined street, burning barrels; the survivor sprints down it with the horde behind
  3. cornered, the cat kicks a street bin over, hops on it and the horde shuffles past
  4. it runs on top of the bin, rolling it down the street to the tower's lit doors, the horde on its heels
  5. the doors open, the bin rolls in with the cat; the title and "Enter Building", zombies piling up outside

Shots are joined by short fades. Any key skips to the title; another key goes into the lobby.
The set is in street.py, the zombies in zombie.py; the survivor is the player's own model.
"""
import math
import random

from ursina import Entity, Text, Vec3, camera, color, destroy, window

from .floor import box, glow, prop
from .street import Street
from .world import ASSETS, floor_y, point_camera, set_exposure
from .cat import Cat, available as cat_available
from .zombie import Horde, Zombie, available as zombies_available

#      city   chase  hide   dash   title
SHOTS = (10.0, 5.0, 4.6, 4.4, 4.2)
FADE = 0.4
SKY = (150, 124, 104)
LINES = ("The city fell in a single day.",
         "Whatever was left of it, they took.",
         "Anywhere they can't see you.",
         "The tower. Go.",
         "")


def _ease(t):
    return t * t * (3 - 2 * t)


def _lerp(a, b, k):
    return a + (b - a) * k


class Intro:
    def __init__(self, lobby, count, end_pos, end_target):
        fx0, fy0, fx1, fy1 = self.fp = lobby.fp
        self.cx, self.cz = (fx0 + fx1) / 2, -(fy0 + fy1) / 2
        self.w, self.d = fx1 - fx0 + 2.2, fy1 - fy0 + 2.2
        self.top, self.bottom = floor_y(count - 1) - 0.3, floor_y(0)
        self.end_pos, self.end_target = end_pos, end_target
        self.door = Vec3(self.cx, self.bottom, self.cz - self.d / 2 - 1.2)   # just outside the entrance
        self.root = Entity()
        self.leaves = []
        self._world()
        self._cast()
        self.overlay = Entity(parent=camera.ui, model='quad', scale=(4, 2), color=color.rgba(0, 0, 0, 0), z=-1)
        self.vignette = Entity(parent=camera.ui, model='quad', texture='textures/vignette',
                               scale=(window.aspect_ratio, 1), color=color.rgba(255, 255, 255, 120), z=-0.5)
        self.title = Text('BLOXORZ', origin=(0, 0), y=0.2, scale=6, color=color.rgba(240, 232, 220, 0))
        self.sub = Text('T O W E R', origin=(0, 0), y=0.08, scale=2.4, color=color.rgba(226, 92, 76, 0))
        self.line = Text('', origin=(0, 0), y=-0.33, scale=1.5, color=color.rgba(226, 222, 214, 0))
        self.button = Text('  Enter Building  ', origin=(0, 0), position=(0.55, -0.36), scale=1.8,
                           color=color.rgba(255, 255, 255, 0))
        self.frame = Entity(parent=camera.ui, model='quad', position=(0.55, -0.36), scale=(0.36, 0.09),
                            color=color.rgba(20, 22, 34, 0), z=0.1)
        self._grain()
        self.skip = Text('press any key to skip', origin=(0, 0), y=-0.44, scale=1,
                         color=color.rgba(220, 220, 230, 160))
        self.t, self.done, self._lit_for = 0.0, False, None
        self.apply()

    def light(self, sun_np):
        """The street is lit brighter than the floors inside; the game restores it on destroy."""
        self.sun = sun_np
        sun_np.setPos(self.cx - 60, self.bottom + 70, self.cz + 20)
        sun_np.lookAt(self.cx, self.bottom, self.street.z0 - 30)
        set_exposure(sun_np, 2.1, 1.9)
        c = sun_np.node().getColor()                               # the light is orange through the smoke
        sun_np.node().setColor((c[0], c[1] * 0.78, c[2] * 0.58, c[3]))

    # ---- the set ----
    def _world(self):
        from panda3d.core import Fog
        rng = random.Random(4)
        cx, cz, b = self.cx, self.cz, self.bottom
        fog = Fog('smoke')
        fog.setColor(0.60, 0.49, 0.41)
        fog.setExpDensity(0.0036)
        self.root.setFog(fog)
        self.street = Street(cx, cz - self.d / 2 - 1.0, length=76, width=13)
        self.street.root.reparent_to(self.root)
        self.street.root.y = b
        self.bin0 = Vec3(self.street.bin.x, 0, self.street.bin.z)             # where the bin first stood
        self.lying = Vec3(self.bin0.x - self.street.bin_r - self.street.bin_h / 2, 0, self.bin0.z)   # and where it comes to rest
        if (ASSETS / 'models' / 'tower.glb').exists():
            tower = prop(self.root, 'tower', Vec3(cx, b, cz), 0, 1)
            self._doors(tower)

    def _doors(self, tower):
        """Two glass leaves over the tower's lit entrance (which is part of the model) that slide apart, with a
        dim lobby behind them. The entrance is 2.4 wide and 1.8 high, its glass 1.5 behind the canopy's front."""
        m = tower.children[0].model_bounds
        z = self.cz + (m.start.z + 1.5 - 0.06) - m.center.z                     # the glass plane, in world z
        y = self.bottom + 0.1
        self.door_z = z
        box(self.root, Vec3(self.cx, y + 0.9, z - 0.03), (2.4, 1.8, 0.02), color.rgb(70, 48, 30))   # the lobby
        glow(self.root, Vec3(self.cx, y + 1.7, z - 0.06), (2.2, 0.06, 0.02), color.rgb(255, 214, 140))
        self.leaves = [glow(self.root, Vec3(self.cx + side * 0.3, y + 0.9, z - 0.09), (1.2, 1.8, 0.04),
                            color.rgb(255, 228, 150)) for side in (-1, 1)]
        self._leaf_open = 0.0

    def _open_doors(self, v):
        for i, leaf in enumerate(self.leaves):
            leaf.x = self.cx + (-1 if i == 0 else 1) * (0.6 + 1.2 * v)

    def _cast(self):
        """The survivor (the player's own model) and the horde."""
        self.hero = None
        self.horde, self.figure, self.strays, self.guards, self.crowd, self.lining = None, None, None, None, None, None
        if zombies_available():
            pts = []                                               # the dead, spread over the whole city
            for x, z in self.street.block_spots[:18]:
                pts.append(Vec3(x + random.uniform(-9, 9), self.bottom, z + random.uniform(-9, 9)))
            for _ in range(10):
                x = self.cx + random.choice((-1, 1)) * random.uniform(4.0, 8.0)       # beside the route, never on it
                pts.append(Vec3(x, self.bottom, self.street.z0 - random.uniform(8, 70)))
            for p in pts:                                           # keep the bin's route (a strip down the avenue) clear
                if abs(p.x - self.cx) < 4.0 and p.z > self.street.z0 - 60:
                    p.x = self.cx + (4.5 if p.x >= self.cx else -4.5) + random.uniform(0, 2)
            self.strays = Horde(pts, parent=self.root, yaw=0)
            self.lining = Horde([Vec3(x, self.bottom, z) for x, z in self.street.lining], parent=self.root, yaw=0)
            self.crowd = Horde([Vec3(x, self.bottom, z) for x, z in self.street.crowd_spots], parent=self.root, scale=1.3)
            self.guards = Horde([Vec3(p.x, self.bottom, p.z) for p in self.street.gate_spots],
                                parent=self.root, yaw=180)             # on watch at the checkpoint
            z0 = self.street.z0
            pts = [Vec3(self.cx + random.uniform(-4, 4), self.bottom, z0 - 42 - random.uniform(0, 9))
                   for _ in range(6)]
            self.horde = Horde(pts, parent=self.root, yaw=0)
            # the cat: runs from the horde, knocks the bin over, rides it into the tower
            self.figure = Cat(Vec3(self.cx - 1.2, self.bottom, z0 - 34), 180, parent=self.root) if cat_available() \
                else Zombie(Vec3(self.cx - 1.2, self.bottom, z0 - 34), 0, kind=1, parent=self.root)
            self.hero = self.figure
            self.hero_holder = self.figure.root

    def _grain(self):
        self.noise = Entity(parent=camera.ui, model='quad', texture='textures/noise', z=-0.6,
                            scale=(window.aspect_ratio, 1), color=color.rgba(255, 255, 255, 12))
        self.noise.texture_scale = (window.aspect_ratio * 3, 3)

    # ---- the action ----
    # The street is a corridor along z: the tower (and its doors) at z0, the ruins stretching to z0 - 76.
    # Everything is placed along that line so the buildings frame each shot instead of blocking it.
    def _act(self, i, k, dt):
        """Move the cast for shot ``i`` at progress ``k``."""
        b, z0 = self.bottom, self.street.z0
        bin_pos = self.bin0
        if self.horde is None:
            return
        if self.strays is not None:                                # the city keeps shambling all the way through
            self.strays.update(dt * 0.6, stride=4)
        if self.guards is not None:
            self.guards.update(dt * 0.5, stride=2)
        if self.crowd is not None:
            self.crowd.update(dt * 0.6, stride=4)
        if self.lining is not None:
            self.lining.update(dt * 0.6, stride=2)
        if i >= 1 and self.figure is not None and self.figure.root.enabled:     # the dead the cat runs past go after it
            cp = self.figure.root.position
            for h in (self.strays, self.crowd, self.guards, self.lining):
                if h is not None:
                    h.alarm(cp, 7.0)
                    h.run(dt, cp)
        if self.leaves:
            self._open_doors(_ease(min(1.0, max(0.0, (k - 0.5) / 0.4))) if i == 3 else
                             (1.0 - _ease(min(1.0, max(0.0, (k - 0.55) / 0.25))) if i == 4 else 0.0))
        if i == 0:                                                 # the fly-over: nobody is acting yet
            if self.figure:
                self.figure.root.enabled = False
            if self.hero:
                self.hero_holder.enabled = False
            self.horde.update(dt * 0.5)
        elif i == 1:                                               # sprinting up the street, horde behind
            if self.figure:
                self.figure.root.enabled = True
                self.figure.root.position = Vec3(_lerp(bin_pos.x + 4.5, bin_pos.x + 1.2, k * k), b,
                                                 _lerp(z0 - 34, bin_pos.z - 2.2, k))
                self.figure.root.rotation_y = 180                  # facing the camera, running towards it
                self.figure.pose(self.t * 2.6, walking=True)
            self.horde.update(dt, self.figure.root.position if self.figure else None, speed=2.1, stop_at=6.0)
        elif i == 2:                                               # the cat kicks the bin over and hops on it
            cat, st = self.figure, self.street
            bx, bz = self.bin0.x, self.bin0.z
            r, h = st.bin_r, st.bin_h
            theta = 90 * _ease(max(0.0, min(1.0, (k - 0.32) / 0.28)))
            st.tip_bin(theta, bx, bz, toward=-1)
            if cat:
                cat.root.enabled = True
                if k < 0.30:                                       # the last few strides to the bin
                    f = k / 0.30
                    cat.root.position = Vec3(_lerp(bx + 1.2, bx + 1.7, f), b, _lerp(bz - 2.2, bz, f))
                    cat.root.rotation_y = _lerp(180, 90, _ease(f))  # swings round to face the bin
                    cat.pose(self.t * 2.6, True)
                elif k < 0.60:                                     # the kick: it springs at the bin and holds there
                    f = (k - 0.30) / 0.30
                    cat.root.position = Vec3(bx + 1.7 - 0.5 * math.sin(math.pi * f) * 0.4, b + 0.5 * math.sin(math.pi * min(1.0, f * 1.6)), bz)
                    cat.root.rotation_y = 90
                    cat.show('Run_F', 1 if f < 0.5 else 4)
                else:                                              # up onto the fallen bin
                    f = _ease((k - 0.60) / 0.22)
                    top = Vec3(st.bin.x, st.bin_r * 2, st.bin.z)
                    cat.root.position = Vec3(_lerp(bx + 1.7, top.x, f), b + _lerp(0, top.y, f) + 1.3 * math.sin(math.pi * f), _lerp(bz, top.z, f))
                    cat.root.rotation_y = _lerp(90, 180, _ease((k - 0.7) / 0.3)) if k > 0.7 else 90
                    cat.show('Run_F', 4 if f < 0.9 else 0)
            self.horde.update(dt, Vec3(bx + 8, b, bz + 4), speed=1.3, stop_at=1.0)
        elif i == 3:                                               # riding the bin to the doors, running on top
            cat, st = self.figure, self.street
            e = _ease(k)
            rest = self.lying
            x = _lerp(rest.x, self.door.x, e)
            z = _lerp(rest.z, self.door.z - 1.4, e)
            st.bin.position = Vec3(x, st.bin_r, z)
            st.bin_spin.rotation_x = -math.degrees((z - rest.z) / st.bin_r)       # rolls as it travels
            if cat:
                cat.root.enabled = True
                d = _ease(max(0.0, (k - 0.72) / 0.25))             # the door is lower than cat + bin: it hops off ahead of it
                cat.root.position = Vec3(x, b + st.bin_r * 2 * (1 - d) + 0.9 * math.sin(math.pi * d), z + 2.4 * d)
                cat.root.rotation_y = 180                          # running towards the doors, on top
                cat.pose(self.t * 3.2, True)
            self.horde.update(dt, cat.root.position if cat else None, speed=2.6, stop_at=7.0)
        else:                                                      # through the doors: the bin rolls into the lobby
            cat, st = self.figure, self.street
            run = _ease(min(1.0, k / 0.7))
            z = _lerp(self.door.z - 1.4, self.cz + 1.0, run)
            st.bin.position = Vec3(self.door.x, st.bin_r, z)
            st.bin_spin.rotation_x = -math.degrees((z - self.lying.z) / st.bin_r)
            vis = k < 0.8
            st.bin.enabled = vis
            if cat:
                cat.root.enabled = vis
                cat.root.position = Vec3(self.door.x, b, z + 2.4 + 2.0 * run)    # the cat runs in first, the bin rolls after it
                cat.root.rotation_y = 180
                cat.pose(self.t * 3.2, True)
            self.horde.set_lunge(min(1.0, k * 1.6))
            self.horde.update(dt, cat.root.position if cat else None, speed=1.9,
                              stop_at=7.0 + 3.0 * k)                   # they pile up at the door

    # ---- the camera ----
    def _shot(self, i, k):
        cx, b, z0 = self.cx, self.bottom, self.street.z0
        bin_pos = self.bin0
        if i == 0:
            if k < 0.5:   # first from high above at an angle: smoking blocks, fires, the dead in the streets, ending on the helipad
                u = k * 2
                pad = self.street.pad
                return (Vec3(_lerp(cx - 38, cx + 8, u), b + _lerp(48, 32, u), _lerp(z0 - 18, z0 - 56, u)),
                        Vec3(_lerp(cx, pad.x, u), _lerp(b + 2, pad.y, u), _lerp(z0 - 58, pad.z, u)))
            u = (k - 0.5) * 2   # then down on the ground: through the checkpoint gate and along the street towards the tower
            z = _lerp(self.street.gate_z - 9, self.street.gate_z + 36, u)
            return (Vec3(_lerp(cx + 1.2, cx - 1.6, u), b + _lerp(3.4, 1.7, u), z),
                    Vec3(cx - 0.4, b + _lerp(2.6, 2.0, u), z + 16))
        if i == 1:      # down the street, the runner coming at us, ruins either side
            return (Vec3(cx + 5.2, b + 2.3, _lerp(z0 - 12, z0 - 17, k)),
                    Vec3(bin_pos.x + 2.5, b + 1.2, _lerp(z0 - 31, bin_pos.z - 3, k)))
        if i == 2:      # beside the bin as the cat knocks it over
            a = math.radians(_lerp(24, 40, k))
            return (Vec3(bin_pos.x + math.sin(a) * 7.5, b + 2.0, bin_pos.z + math.cos(a) * 7.5),
                    Vec3(bin_pos.x - 0.9, b + 0.9, bin_pos.z))
        if i == 3:      # trailing the cat and the rolling bin, the lit doors ahead
            e = _ease(k)
            x = _lerp(self.lying.x, self.door.x, e)
            z = _lerp(self.lying.z, self.door.z - 1.4, e)
            return Vec3(x + 3.4, b + 2.7, z - 6.0), Vec3(x - 0.3, b + 1.2, z + 2.5)
        return (Vec3(cx + _lerp(5.0, 3.2, k), b + 2.0, self.door.z - _lerp(15, 12, k)),
                Vec3(cx, b + 4.2, self.cz))

    def skip_or_enter(self):
        if self.t < sum(SHOTS):
            self.t = sum(SHOTS)
        else:
            self.done = True

    def step(self, dt):
        self.t += dt
        self.apply(dt)

    def apply(self, dt=0.0):
        t, i = self.t, 0
        while i < len(SHOTS) - 1 and t > SHOTS[i]:
            t -= SHOTS[i]
            i += 1
        k = min(1.0, t / SHOTS[i])
        if getattr(self, 'sun', None) is not None and self._lit_for is None:
            self.light(self.sun)
            self._lit_for = i
        self._act(i, k, dt)
        self.street.flicker(self.t)
        pos, target = self._shot(i, _ease(k))
        camera.position = pos
        point_camera(camera, target)
        window.color = color.rgb(*SKY)
        fade = 0.0                                                             # dip to black between shots
        if i > 0 and t < FADE:
            fade = 1 - t / FADE
        elif i < len(SHOTS) - 1 and SHOTS[i] - t < FADE:
            fade = 1 - (SHOTS[i] - t) / FADE
        if i == 0:                                                             # the cut from ground to air
            fade = max(fade, 1 - min(1.0, abs(t - SHOTS[0] / 2) / (FADE / 2)))
        self.overlay.color = color.rgba(0, 0, 0, int(255 * fade))
        self.noise.texture_offset = (random.random(), random.random())   # film grain flicker
        show = min(1.0, t / 0.6) * min(1.0, (SHOTS[i] - t) / 0.6) * (1 - fade)
        self.line.text = LINES[i]
        self.line.color = color.rgba(226, 222, 214, int(210 * max(0.0, show)))
        a = 0.0 if i < 4 else min(1.0, t / 1.2)
        self.title.color = color.rgba(240, 232, 220, int(255 * a))
        self.sub.color = color.rgba(226, 92, 76, int(255 * a))
        ready = self.t >= sum(SHOTS)
        self.button.color = color.rgba(255, 255, 255, int(255 * a) if i == 4 else 0)
        self.frame.color = color.rgba(20, 22, 34, int(200 * a) if i == 4 else 0)
        self.skip.enabled = not ready and i < 4

    def destroy(self):
        if getattr(self, 'sun', None) is not None:
            set_exposure(self.sun, 1.0, 1.0)
        if self.horde:
            self.horde.destroy()
        if self.strays:
            self.strays.destroy()
        if self.guards:
            self.guards.destroy()
        if self.crowd:
            self.crowd.destroy()
        if self.lining:
            self.lining.destroy()
        if self.figure:
            self.figure.destroy()
        self.street.destroy()
        for e in (self.root, self.overlay, self.vignette, self.noise, self.title, self.sub, self.line,
                  self.button, self.frame, self.skip):
            destroy(e)
