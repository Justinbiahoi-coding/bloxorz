"""The player in 3D: a trash can (tools/blender_trashcan.py) that fills the 1 x 1 x 2 block.

Tipping over or standing up is a real quarter turn about the leading bottom edge. Lying on its side and
moving across its own axis, the can rolls like a barrel: it slides one cell while spinning about its axis.
Split cubes are short, squat cans.
"""
import math

from ursina import Entity, Vec3, color, destroy

from ui.blockfx import make_box, rolls_to

from .floor import TILE_TOP
from .world import ASSETS

ACTIVE = color.rgb(255, 150, 40)
HAS_MODEL = (ASSETS / 'models' / 'player_can.glb').exists()


def _boxes(session, state):
    cells = session.block_cells(state)
    if state.split:
        return [make_box([c], True) for c in cells]
    return [make_box(cells, False)]


def _centre(box, base):
    x0, y0, sx, sy, sz = box
    return Vec3(x0 - 0.5 + sx / 2, base + TILE_TOP + sz / 2, -(y0 - 0.5 + sy / 2))


def _piece(box, base, ring):
    """holder (moves/tips) -> spinner (barrel roll) -> can (orientation for this pose)."""
    x0, y0, sx, sy, sz = box
    holder = Entity(position=_centre(box, base))
    spinner = Entity(parent=holder)
    if HAS_MODEL:
        can = Entity(parent=spinner, model='models/player_can', scale=(1, sz / 2 if sz == 1 and sx == sy else 1, 1))
        if sx == 2:
            can.rotation_z = 90                       # lying east-west
        elif sy == 2:
            can.rotation_x = -90                      # lying north-south, face up
        for mat in can.findAllMaterials():
            mat.setMetallic(0)
    else:
        Entity(parent=spinner, model='cube', scale=(sx, sz, sy), color=color.rgb(62, 112, 208))
    if ring:                                          # the controlled split cube wears a ring
        Entity(parent=holder, model='cube', y=sz / 2 + 0.02, scale=(1.0, 0.03, 1.0), color=ACTIVE)
    holder.spinner = spinner
    return holder


class Block:
    def __init__(self):
        self.pieces, self.pivot, self.roll = [], None, None

    def clear(self):
        for e in self.pieces:
            destroy(e)
        if self.pivot:
            destroy(self.pivot)
        self.pieces, self.pivot, self.roll = [], None, None

    def place(self, session, state, base):
        self.clear()
        for i, box in enumerate(_boxes(session, state)):
            self.pieces.append(_piece(box, base, state.split and i == state.active))

    def start_roll(self, session, before, after, action, d, base):
        """Begin animating the move; False when it is not a plain roll (then just place the new state)."""
        if action == 'SWITCH' or before.split != after.split:
            return False
        idx = before.active if before.split else 0
        start, end = _boxes(session, before)[idx], _boxes(session, after)[idx]
        if not rolls_to(start, d, end):
            return False
        self.place(session, before, base)
        wd = Vec3(d[0], 0, -d[1])                                     # engine y grows southwards = world -z
        x0, y0, sx, sy, sz = start
        if HAS_MODEL and sz == 1 and start[2:] == end[2:] and not before.split:
            self.roll = ('barrel', wd, session, after, base, idx, _centre(start, base), _centre(end, base))
            return True
        c = _centre(start, base)
        self.pivot = Entity(position=c + Vec3(wd.x * sx / 2, -sz / 2, wd.z * sy / 2))
        self.pieces[idx].world_parent = self.pivot
        self.roll = ('tip', wd, session, after, base, idx)
        return True

    def set_progress(self, t):
        e = t * t * (3 - 2 * t)
        kind, wd = self.roll[0], self.roll[1]
        if kind == 'barrel':
            _, _, _, _, _, idx, c0, c1 = self.roll
            piece = self.pieces[idx]
            piece.position = c0 + (c1 - c0) * e
            spin = math.degrees(1 / 0.46) * e                         # distance / radius
            if wd.x:
                piece.spinner.rotation_z = -spin * wd.x
            else:
                piece.spinner.rotation_x = spin * wd.z
            return
        a = 90 * e
        if wd.x:
            self.pivot.rotation_z = a * wd.x
        else:
            self.pivot.rotation_x = a * wd.z

    def finish(self):
        _, _, session, after, base = self.roll[:5]
        self.place(session, after, base)

    @property
    def rolling(self):
        return self.roll is not None
