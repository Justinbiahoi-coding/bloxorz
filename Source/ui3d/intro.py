"""Opening cutscene: the day the city fell (bright daylight, after the Zombie Barricades trailer).

  1. ten seconds: five low on the ground, gliding in through a checkpoint gate and down the ruined street;
     five from high above at an angle, over the autumn trees and the roofs to a rooftop helipad
  2. a ruined street, burning barrels; the survivor sprints down it with the horde behind
  3. cornered: they dive into a street bin, the lid rocks shut, the horde shuffles past and loses them
  4. the bin gets up and runs for the tower's lit doors; the horde turns and comes after it
  5. at the doors: the title and "Enter Building", zombies closing in

Shots are joined by short fades. Any key skips to the title; another key goes into the lobby.
The set is in street.py, the zombies in zombie.py; the survivor is the player's own model.
"""
import math
import random

from ursina import Entity, Text, Vec3, camera, color, destroy, window

from .floor import prop
from .street import Street
from .world import ASSETS, floor_y, point_camera, set_exposure
from .zombie import Horde, Zombie, available as zombies_available

#      city   chase  hide   dash   title
SHOTS = (10.0, 5.0, 4.6, 4.4, 3.0)
FADE = 0.4
SKY = (150, 196, 236)
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
        set_exposure(sun_np, 1.45, 1.5)

    # ---- the set ----
    def _world(self):
        from panda3d.core import Fog
        rng = random.Random(4)
        cx, cz, b = self.cx, self.cz, self.bottom
        fog = Fog('smoke')
        fog.setColor(0.70, 0.80, 0.90)
        fog.setExpDensity(0.0022)
        self.root.setFog(fog)
        self.street = Street(cx, cz - self.d / 2 - 1.0, length=76, width=13)
        self.street.root.reparent_to(self.root)
        self.street.root.y = b
        if (ASSETS / 'models' / 'tower.glb').exists():
            prop(self.root, 'tower', Vec3(cx, b, cz), 0, 1)

    def _cast(self):
        """The survivor (the player's own model) and the horde."""
        self.hero = None
        if (ASSETS / 'models' / 'player_actor' / 'player.glb').exists():
            from direct.actor.Actor import Actor
            from panda3d.core import Filename
            holder = Entity(parent=self.root)
            self.hero = Actor(Filename.fromOsSpecific(str(ASSETS / 'models/player_actor/player.glb')))
            self.hero.reparentTo(holder)
            self.hero.setScale(2.0 / 2.279)
            for m in self.hero.findAllMaterials():
                m.setMetallic(0)
            self.hero.loop('run')
            self.hero.setPlayRate(2.4, 'run')
            self.hero_holder = holder
            holder.enabled = False                                 # shot 1 shows a silhouette instead
        self.horde, self.figure, self.strays, self.guards = None, None, None, None
        if zombies_available():
            pts = []                                               # the dead, spread over the whole city
            for x, z in self.street.block_spots[:18]:
                pts.append(Vec3(x + random.uniform(-9, 9), self.bottom, z + random.uniform(-9, 9)))
            for _ in range(10):
                pts.append(Vec3(self.cx + random.uniform(-7, 7), self.bottom,
                                self.street.z0 - random.uniform(10, 70)))
            self.strays = Horde(pts, parent=self.root, yaw=0)
            self.guards = Horde([Vec3(p.x, self.bottom, p.z) for p in self.street.gate_spots],
                                parent=self.root, yaw=180)             # on watch at the checkpoint
            z0 = self.street.z0
            pts = [Vec3(self.cx + random.uniform(-4, 4), self.bottom, z0 - 42 - random.uniform(0, 9))
                   for _ in range(6)]
            self.horde = Horde(pts, parent=self.root, yaw=0)
            # the survivor before the bin: one zombie mesh, blacked out, reads as a person in the dark
            self.figure = Zombie(Vec3(self.cx - 1.2, self.bottom, z0 - 34), 0, kind=1, parent=self.root)
            self.figure.root.setColorScale(0.07, 0.08, 0.12, 1)
            self.figure.root.setLightOff()

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
        bin_pos = self.street.bin.position
        if self.horde is None:
            return
        if self.strays is not None:                                # the city keeps shambling all the way through
            self.strays.update(dt * 0.6)
        if self.guards is not None:
            self.guards.update(dt * 0.5)
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
                self.figure.root.rotation_y = 0                    # facing the camera, running towards it
                self.figure.pose(self.t * 2.6, walking=True)
            self.horde.update(dt, self.figure.root.position if self.figure else None, speed=2.1, stop_at=6.0)
        elif i == 2:                                               # into the bin, lid down, horde drifts past
            if self.figure:
                dive = _ease(min(1.0, k / 0.35))
                self.figure.root.position = Vec3(_lerp(bin_pos.x + 1.2, bin_pos.x, dive), b - 1.9 * dive,
                                                 _lerp(bin_pos.z - 2.2, bin_pos.z, dive))
                self.figure.root.enabled = dive < 0.97
            self.street.bin.rotation_z = 8 * math.sin(k * 24) * max(0.0, 1 - k * 2.6)
            lift = math.sin(math.pi * min(1.0, k / 0.42)) if k < 0.42 else 0.0
            self.street.lid.y = 1.9 + 0.75 * lift
            self.street.lid.rotation_x = 46 * lift
            self.horde.update(dt, Vec3(bin_pos.x + 8, b, bin_pos.z + 4), speed=1.3, stop_at=1.0)
        elif i == 3:                                               # the bin gets up and runs for the doors
            self.street.bin.enabled = k < 0.05
            if self.hero:
                self.hero_holder.enabled = True
                self.hero_holder.position = Vec3(_lerp(bin_pos.x, self.door.x, _ease(k)), b,
                                                 _lerp(bin_pos.z, self.door.z - 1.4, _ease(k)))
                self.hero_holder.rotation_y = 180                  # running away from the camera, towards the doors
            self.horde.update(dt, self.hero_holder.position if self.hero else None, speed=2.6, stop_at=2.4)
        else:                                                      # at the doors; they are closing in
            self.street.bin.enabled = False
            if self.hero:
                self.hero_holder.enabled = True
                self.hero_holder.position = Vec3(self.door.x, b, self.door.z - 1.4)
                self.hero_holder.rotation_y = 180
            self.horde.set_lunge(min(1.0, k * 1.6))
            self.horde.update(dt, self.hero_holder.position if self.hero else None, speed=1.9, stop_at=3.2)

    # ---- the camera ----
    def _shot(self, i, k):
        cx, b, z0 = self.cx, self.bottom, self.street.z0
        bin_pos = self.street.bin.position
        if i == 0:
            if k < 0.5:   # low on the ground: through the checkpoint gate and down the street towards the tower
                u = k * 2
                z = _lerp(self.street.gate_z - 9, self.street.gate_z + 36, u)
                return (Vec3(_lerp(cx + 1.2, cx - 1.6, u), b + _lerp(3.4, 1.7, u), z),
                        Vec3(cx - 0.4, b + _lerp(2.6, 2.0, u), z + 16))
            u = (k - 0.5) * 2   # high and oblique over the trees and roofs, ending on the rooftop helipad
            pad = self.street.pad
            return (Vec3(_lerp(cx - 46, cx + 4, u), b + _lerp(54, 46, u), _lerp(z0 - 78, z0 - 54, u)),
                    Vec3(_lerp(cx - 8, pad.x, u), _lerp(b + 2, pad.y, u), _lerp(z0 - 46, pad.z, u)))
        if i == 1:      # down the street, the runner coming at us, ruins either side
            return (Vec3(cx + 5.2, b + 2.3, _lerp(z0 - 12, z0 - 17, k)),
                    Vec3(bin_pos.x + 2.5, b + 1.2, _lerp(z0 - 31, bin_pos.z - 3, k)))
        if i == 2:      # close on the bin, drifting round it
            a = math.radians(_lerp(26, 56, k))
            return (Vec3(bin_pos.x + math.sin(a) * 8.5, b + 2.3, bin_pos.z + math.cos(a) * 8.5),
                    Vec3(bin_pos.x + 1.2, b + 1.1, bin_pos.z - 2.5))
        if i == 3:      # trailing the runner, the lit doors ahead
            z = _lerp(bin_pos.z - 5.5, self.door.z - 9.0, _ease(k))
            return Vec3(cx + 2.2, b + 2.7, z), Vec3(cx, b + 2.4, z + 11)
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
        if self.figure:
            self.figure.destroy()
        if self.hero:
            self.hero.cleanup()
            destroy(self.hero_holder)
        self.street.destroy()
        for e in (self.root, self.overlay, self.vignette, self.noise, self.title, self.sub, self.line,
                  self.button, self.frame, self.skip):
            destroy(e)
