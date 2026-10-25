"""Voxel zombies, animated in code from rigid parts (tools/blender_zombie.py).

The parts (head, torso, arm_l, arm_r, legs) hang off a root at the feet and are rotated at their joints,
so one small model gives a shamble, a lurch forward and a lunging bite. ``Horde`` keeps a group of them
walking towards a point, each with its own offset so they do not move in lockstep.
"""
import json
import math
import random

from ursina import Entity, Vec3, color, destroy

from .world import ASSETS

DIR = ASSETS / 'models' / 'zombie'
RIG = json.loads((DIR / 'zombie_rig.json').read_text()) if (DIR / 'zombie_rig.json').exists() else None
KINDS = sorted({int(p.name[3]) for p in DIR.glob('zed?_torso.glb')}) if DIR.exists() else []
PARTS = ('legs', 'torso', 'head', 'arm_l', 'arm_r')


def available():
    return RIG is not None and bool(KINDS)


class Zombie:
    """One zombie standing at ``pos`` facing ``yaw``. ``phase`` staggers its walk cycle."""

    def __init__(self, pos, yaw=0.0, kind=None, scale=1.0, parent=None, phase=None):
        self.root = Entity(parent=parent, position=pos, rotation_y=yaw, scale=scale)
        kind = kind if kind is not None else random.choice(KINDS)
        self.parts = {}
        for name in PARTS:
            jx, jy, jz = RIG['joints'][name]
            e = Entity(parent=self.root, model='models/zombie/zed%d_%s' % (kind, name), position=(jx, jy, jz))
            for m in e.findAllMaterials():
                m.setMetallic(0)
            self.parts[name] = e
        self.phase = random.uniform(0, math.tau) if phase is None else phase
        self.speed = random.uniform(0.85, 1.15)
        self.lunge = 0.0                                  # 0 shambling .. 1 arms out, biting
        self.pose(0.0)

    def pose(self, t, walking=False):
        """Shamble: a slow sway, the head lolling, arms swinging or reaching out when lunging."""
        a = t * self.speed * (6.0 if walking else 2.0) + self.phase
        s, L = math.sin(a), self.lunge
        self.root.rotation_z = (1 - L) * 4 * math.sin(a * 0.5) + L * 2
        self.parts['torso'].rotation_x = -6 - 14 * L + (2 * s if walking else 0)
        self.parts['head'].rotation_x = 8 + 10 * L
        self.parts['head'].rotation_z = 6 * math.sin(a * 0.37)
        for i, name in enumerate(('arm_l', 'arm_r')):
            side = -1 if i == 0 else 1
            arm = self.parts[name]
            arm.rotation_x = (1 - L) * (14 + (26 * s * side if walking else 4 * math.sin(a * 0.6))) - 78 * L
            arm.rotation_z = side * (6 + 16 * L)
        self.parts['legs'].rotation_x = (3 * s if walking else 0) - 4 * L

    def walk_to(self, pos, dt, speed=1.4, turn=6.0):
        """Step towards ``pos``; returns the distance left."""
        d = Vec3(pos.x - self.root.x, 0, pos.z - self.root.z)
        dist = d.length()
        if dist > 1e-3:
            want = math.degrees(math.atan2(-d.x, -d.z))
            cur = self.root.rotation_y
            self.root.rotation_y = cur + ((want - cur + 180) % 360 - 180) * min(1.0, dt * turn)
            step = min(dist, speed * self.speed * dt)
            self.root.position += d.normalized() * step
        return dist

    def destroy(self):
        destroy(self.root)


class Horde:
    """A pack of zombies. ``chase(target)`` walks them at a point; ``t`` drives the shamble."""

    def __init__(self, points, parent=None, scale=1.0, yaw=0.0):
        self.members = [Zombie(p, yaw + random.uniform(-25, 25), parent=parent, scale=scale) for p in points]
        self.t, self.n = 0.0, 0

    def update(self, dt, target=None, speed=1.4, stop_at=0.0, stride=1):
        """``stride`` > 1 animates only every stride-th zombie each frame (each with the time it missed): a crowd
        of a hundred poses itself in a few frames, and Ursina's property setters are slow."""
        self.t += dt
        self.n += 1
        for i, z in enumerate(self.members):
            if stride > 1 and (i + self.n) % stride:
                continue
            moving = False
            if target is not None:
                moving = z.walk_to(target, dt * stride, speed) > stop_at
            z.pose(self.t, moving)

    def set_lunge(self, k):
        for z in self.members:
            z.lunge = k

    def destroy(self):
        for z in self.members:
            z.destroy()
