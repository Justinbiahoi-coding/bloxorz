"""The rolling block in 3D. A roll is a real quarter turn about the block's leading bottom edge."""
import math

from ursina import Entity, Vec3, color, destroy

from ui.blockfx import make_box, rolls_to

from .floor import TILE_TOP

BLUE, ACTIVE = color.rgb(62, 112, 208), color.rgb(255, 150, 40)


def _boxes(session, state):
    cells = session.block_cells(state)
    if state.split:
        return [make_box([c], True) for c in cells]
    return [make_box(cells, False)]


def _centre(box, base):
    x0, y0, sx, sy, sz = box
    return Vec3(x0 - 0.5 + sx / 2, base + TILE_TOP + sz / 2, -(y0 - 0.5 + sy / 2))


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
        """Static block(s) for ``state`` on the floor whose ground is at height ``base``."""
        self.clear()
        for i, box in enumerate(_boxes(session, state)):
            e = Entity(model='cube', position=_centre(box, base), scale=(box[2], box[4], box[3]), color=BLUE)
            if state.split and i == state.active:                    # the controlled cube wears a ring
                Entity(parent=e, model='cube', y=0.52, scale=(1.08, 0.04, 1.08), color=ACTIVE)
            self.pieces.append(e)

    def start_roll(self, session, before, after, action, d, base):
        """Begin animating the move; False when it is not a plain roll (then just place the new state)."""
        if action == 'SWITCH' or before.split != after.split:
            return False
        idx = before.active if before.split else 0
        start, end = _boxes(session, before)[idx], _boxes(session, after)[idx]
        if not rolls_to(start, d, end):
            return False
        self.place(session, before, base)
        x0, y0, sx, sy, sz = start
        c = _centre(start, base)
        wd = Vec3(d[0], 0, -d[1])                                     # engine y grows southwards = world -z
        edge = c + Vec3(wd.x * sx / 2, -sz / 2, wd.z * sy / 2)
        self.pivot = Entity(position=edge)
        self.pieces[idx].world_parent = self.pivot
        self.roll = (wd, session, after, base)
        return True

    def set_progress(self, t):
        """Turn the rolling piece to fraction t (0..1) of a quarter turn, eased."""
        wd = self.roll[0]
        a = 90 * (t * t * (3 - 2 * t))
        if wd.x:
            self.pivot.rotation_z = a * wd.x
        else:
            self.pivot.rotation_x = a * wd.z

    def finish(self):
        _, session, after, base = self.roll
        self.place(session, after, base)

    @property
    def rolling(self):
        return self.roll is not None
