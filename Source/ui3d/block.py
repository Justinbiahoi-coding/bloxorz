"""The player in 3D: a character (models/player.glb, else our Blender trash can) filling the 1 x 1 x 2 block.

Every move is animated from where the character is to where it ends, so nothing snaps:
  dive    standing -> lying       leaps forward, head first, and lands flat on the two cells
  spring  lying -> standing       pushes up and hops onto the far cell, landing upright
  barrel  lying, across its axis  rolls over like a log
  hop     a split (single-cell) cube tumbling over
The body turns about its own centre while the centre flies along a small arc; a landing squash and a
gentle idle bob are added per frame. The orientation a move ends in is remembered (head left or right,
face up or down), so the next move starts exactly from it.
"""
import math

from ursina import Entity, Vec3, color, destroy

from ui.blockfx import make_box, rolls_to

from .floor import TILE_TOP
from .world import ASSETS

ACTIVE = color.rgb(255, 150, 40)
# models/player.glb (a downloaded character, kept out of git until its licence is known) wins over
# models/player_can.glb (our own Blender trash can)
MODEL = next((n for n in ('player', 'player_can') if (ASSETS / 'models' / (n + '.glb')).exists()), None)
HAS_MODEL = MODEL is not None

# per kind of move: duration (s), arc height (cells), landing squash
MOVES = {'dive': (0.36, 0.55, 0.16),
         'spring': (0.38, 0.70, 0.12),
         'barrel': (0.30, 0.10, 0.06),
         'hop': (0.24, 0.40, 0.10)}


def _smooth(t):
    return t * t * t * (t * (6 * t - 15) + 10)               # smootherstep: no jerk at either end


def _boxes(session, state):
    cells = session.block_cells(state)
    if state.split:
        return [make_box([c], True) for c in cells]
    return [make_box(cells, False)]


def _centre(box, base):
    x0, y0, sx, sy, sz = box
    return Vec3(x0 - 0.5 + sx / 2, base + TILE_TOP + sz / 2, -(y0 - 0.5 + sy / 2))


def _pose(box):
    """'stand', 'ew' (lying along x) or 'ns' (lying along z)."""
    return 'stand' if box[4] == 2 or box[2] == box[3] else ('ew' if box[2] == 2 else 'ns')


DEFAULT = {'stand': (0, 0), 'ew': (0, 90), 'ns': (-90, 0)}   # (rotation_x, rotation_z); ns: face up


def _piece(box, base, ring, orient):
    """holder (position + body orientation) -> spinner (log roll, squash, bob) -> model."""
    x0, y0, sx, sy, sz = box
    holder = Entity(position=_centre(box, base), rotation_x=orient[0], rotation_z=orient[1])
    spinner = Entity(parent=holder)
    if HAS_MODEL:
        short = sz == 1 and sx == sy                           # a split cube: a squat character
        m = Entity(parent=spinner, model='models/' + MODEL, scale=(1, 0.5 if short else 1, 1))
        for mat in m.findAllMaterials():
            mat.setMetallic(0)
    else:
        holder.rotation = (0, 0, 0)
        Entity(parent=spinner, model='cube', scale=(sx, sz, sy), color=color.rgb(62, 112, 208))
    if ring:
        Entity(parent=holder, model='cube', y=0.27 if sz == 1 else 1.02, scale=(1.0, 0.03, 1.0), color=ACTIVE)
    holder.spinner = spinner
    return holder


class Block:
    def __init__(self):
        self.pieces, self.roll = [], None
        self.orient = None                                     # (pose, (rx, rz)) of the main piece
        self.squash, self.clock = 0.0, 0.0

    def clear(self):
        for e in self.pieces:
            destroy(e)
        self.pieces, self.roll = [], None

    def _orient_for(self, box):
        pose = _pose(box)
        if self.orient and self.orient[0] == pose:
            return self.orient[1]
        return DEFAULT[pose]

    def place(self, session, state, base):
        self.clear()
        for i, box in enumerate(_boxes(session, state)):
            orient = self._orient_for(box) if not state.split else (0, 0)
            self.pieces.append(_piece(box, base, state.split and i == state.active, orient))

    @property
    def duration(self):
        return MOVES[self.roll[0]][0] if self.roll else 0.2

    def start_roll(self, session, before, after, action, d, base):
        """Begin animating the move; False when it is not a plain roll (then just place the new state)."""
        if action == 'SWITCH' or before.split != after.split:
            return False
        idx = before.active if before.split else 0
        start, end = _boxes(session, before)[idx], _boxes(session, after)[idx]
        if not rolls_to(start, d, end):
            return False
        self.place(session, before, base)
        wd = Vec3(d[0], 0, -d[1])                                 # engine y grows southwards = world -z
        p0, p1 = _pose(start), _pose(end)
        o0 = (self.pieces[idx].rotation_x, self.pieces[idx].rotation_z)
        if before.split:
            kind, o1 = 'hop', (0, 0)
        elif p0 == 'stand':                                       # head first, in the direction of travel
            kind = 'dive'
            o1 = (0, 90 * wd.x) if p1 == 'ew' else (90 * wd.z, 0)
        elif p1 == 'stand':
            kind, o1 = 'spring', (0, 0)
        else:
            kind, o1 = 'barrel', o0
        self.roll = (kind, wd, session, after, base, idx, _centre(start, base), _centre(end, base), o0, o1, p1)
        return True

    def set_progress(self, t):
        kind, wd, _, _, _, idx, c0, c1, o0, o1, _ = self.roll
        dur, hop, _ = MOVES[kind]
        piece = self.pieces[idx]
        e = _smooth(t)
        arc = math.sin(math.pi * t) * hop
        if kind == 'barrel':                                      # log roll: two little bumps per turn
            piece.position = c0 + (c1 - c0) * e + Vec3(0, abs(math.sin(math.pi * 2 * t)) * hop, 0)
            side = wd.x if piece.rotation_z else -wd.z
            piece.spinner.rotation_y = math.degrees(1 / 0.46) * e * side
            return
        if kind == 'hop':                                         # a cube tumbles a full quarter turn
            piece.position = c0 + (c1 - c0) * e + Vec3(0, arc, 0)
            piece.rotation_z, piece.rotation_x = 90 * wd.x * e, 90 * wd.z * e
            return
        lead = _smooth(min(1.0, t * 1.15))                        # the body turns slightly ahead of the jump
        piece.position = c0 + (c1 - c0) * e + Vec3(0, arc, 0)
        piece.rotation_x = o0[0] + (o1[0] - o0[0]) * lead
        piece.rotation_z = o0[1] + (o1[1] - o0[1]) * lead

    def finish(self):
        kind, _, session, after, base, _, _, _, _, o1, p1 = self.roll
        if not after.split:
            self.orient = (p1, o1)
        self.place(session, after, base)
        self.squash = MOVES[kind][2]                              # landing: squash, then spring back

    def tick(self, dt, idle):
        """Per frame: landing squash recovery and a gentle idle bob."""
        self.clock += dt
        self.squash = max(0.0, self.squash - dt * 0.9)
        k = self.squash * math.cos(self.clock * 40) if self.squash else 0.0
        bob = 0.025 * math.sin(self.clock * 2.6) if idle else 0.0
        if self.roll is None:
            for p in self.pieces:
                p.spinner.scale = Vec3(1 + k * 0.6, 1 - k, 1 + k * 0.6)
                p.spinner.y = bob

    @property
    def rolling(self):
        return self.roll is not None
