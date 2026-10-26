"""A walking character rig for the player, built from rigid parts (tools/blender_split_character.py).

The character never lies down. Its feet show which cells the block covers:
  * one cell   -> feet together on it
  * two cells  -> one foot on each cell: a lunge when the cells line up with where it faces,
                  a wide guard stance (arms up) when they lie across it
Moves:
  * walk  (standing <-> two cells in line, or a single split cube): it turns to face the move and steps,
          one foot then the other, each foot on an arc, arms swinging against the legs
  * hop   (two cells moving sideways to their axis): it keeps the wide guard stance and hops, both feet
          together, with a crouch before and a squash after
The legs are aimed at the feet by a one-bone IK (hip -> foot); the pelvis height follows from the spread.
"""
import json
import math

from ursina import Entity, Vec3, destroy

from .world import ASSETS

PARTS = ASSETS / 'models' / 'player_parts'
RIG = json.load(open(PARTS / 'player_rig.json')) if (PARTS / 'player_rig.json').exists() else None
LEG = RIG['leg_l']['joint'][1] if RIG else 0.94               # hip height = leg length
HIP_X = abs(RIG['leg_l']['joint'][0]) if RIG else 0.25
FOOT_GAP = 0.2                                                 # half distance between feet when together


def available():
    return RIG is not None


def yaw_for(dx, dz):
    """Ursina yaw that makes the character face world direction (dx, dz) (yaw 0 faces -z)."""
    return math.degrees(math.atan2(-dx, -dz))


def to_local(v, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return Vec3(v.x * c - v.z * s, v.y, v.x * s + v.z * c)


def to_world(v, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return Vec3(v.x * c + v.z * s, v.y, -v.x * s + v.z * c)


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


def _lerp_angle(a, b, k):
    d = (b - a + 180) % 360 - 180
    return a + d * k


class Rig:
    """One character. ``scale`` < 1 for the small split cubes."""

    def __init__(self, ground, yaw, scale=1.0):
        self.scale = scale
        self.root = Entity(position=ground, rotation_y=yaw, scale=scale)
        self.pelvis = Entity(parent=self.root, y=LEG)
        self.parts = {}
        for name, d in RIG.items():
            j = d['joint']
            parent = self.pelvis
            pos = Vec3(j[0], j[1] - LEG, j[2])
            e = Entity(parent=parent, model='models/player_parts/player_' + name, position=pos)
            for m in e.findAllMaterials():
                m.setMetallic(0)
            self.parts[name] = e
        self.feet = [None, None]                               # world positions, leg_l then leg_r
        self.guard = 0.0                                       # 0 relaxed .. 1 arms up
        self.swing = 0.0                                       # arm swing phase helper

    # --- posing ---
    @property
    def yaw(self):
        return self.root.rotation_y

    def hip_world(self, i):
        x = (-HIP_X if i == 0 else HIP_X) * self.scale
        return self.root.position + to_world(Vec3(x, 0, 0), self.yaw)

    def pose(self, feet, yaw, lift=(0.0, 0.0), crouch=0.0, bob=0.0, lean=0.0):
        """Place the root between the feet, set the pelvis height and aim both legs."""
        self.root.rotation_y = yaw
        mid = (feet[0] + feet[1]) / 2
        self.root.position = Vec3(mid.x, min(feet[0].y, feet[1].y), mid.z)
        s, L = self.scale, LEG * self.scale
        spread = []
        for i in (0, 1):
            hip = self.hip_world(i)
            d = Vec3(feet[i].x - hip.x, 0, feet[i].z - hip.z).length()
            spread.append(d)
        h = math.sqrt(max(0.0, L * L - min(max(spread), L * 0.92) ** 2))  # legs straight at the widest foot
        h = h * (1 - 0.18 * crouch) + bob * s
        self.pelvis.y = h / s
        self.pelvis.rotation_x = lean
        for i, name in enumerate(('leg_l', 'leg_r')):
            hip = self.hip_world(i) + Vec3(0, h, 0)
            foot = feet[i] + Vec3(0, lift[i], 0)
            v = to_local(foot - hip, yaw)
            vy = min(-0.05, v.y)
            leg = self.parts[name]
            leg.rotation_x = math.degrees(math.atan2(-v.z, -vy)) - lean
            leg.rotation_z = math.degrees(math.atan2(-v.x, -vy))
            reach = v.length() / L                              # a foot nearer than the leg: shorten (knee bend)
            leg.scale_y = min(1.0, max(0.55, reach))
        for i, name in enumerate(('arm_l', 'arm_r')):
            arm = self.parts[name]
            side = -1 if i == 0 else 1
            arm.rotation_x = -55 * self.guard + self.swing * (1 if i == 0 else -1) * (1 - self.guard)
            arm.rotation_z = side * -(8 + 22 * self.guard)
        self.feet = [Vec3(feet[0]), Vec3(feet[1])]

    def destroy(self):
        destroy(self.root)


def feet_for(cells, yaw, ground_y):
    """World foot positions for the cells the block covers (one or two), given the facing."""
    if len(cells) == 1:
        c = cells[0]
        side = to_world(Vec3(FOOT_GAP, 0, 0), yaw)
        return [Vec3(c.x, ground_y, c.z) - side, Vec3(c.x, ground_y, c.z) + side]
    a, b = (Vec3(c.x, ground_y, c.z) for c in cells)
    la, lb = to_local(a - (a + b) / 2, yaw), to_local(b - (a + b) / 2, yaw)
    if abs(la.x - lb.x) > 0.1:                                # across the facing: left foot on the left cell
        return [a, b] if la.x < lb.x else [b, a]
    return [a, b] if la.z < lb.z else [b, a]                 # in line: leg_l in front (lunge)
