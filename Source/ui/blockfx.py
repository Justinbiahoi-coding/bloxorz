"""A 3D-looking block for the top-down view: an obliquely projected box that really rolls over its edge.

Coordinates are in cells: x east, y south (screen down), z up. A standing block is 1x1x2, a lying one
2x1x1 or 1x2x1, a split cube 1x1x1. The camera is above and south, so you see the top and south faces.
"""
import math
from types import SimpleNamespace

import pygame

TILT = 0.55                      # screen rise per unit of height
BASE, OUTLINE, RING = (62, 112, 208), (16, 32, 80), (255, 150, 40)
LIGHT = (-0.35, 0.45, 0.82)      # direction towards the light (from the top, front, left)
ROLL_MS = 170
# face normal, corner indices; corner i = (i & 1, i >> 1 & 1, i >> 2 & 1) of the box
FACES = (((0, 0, 1), (4, 5, 7, 6)), ((0, 0, -1), (0, 1, 3, 2)), ((0, 1, 0), (2, 3, 7, 6)),
         ((0, -1, 0), (0, 1, 5, 4)), ((1, 0, 0), (1, 3, 7, 5)), ((-1, 0, 0), (0, 2, 6, 4)))


def make_box(cells, cube):
    xs, ys = [c[0] for c in cells], [c[1] for c in cells]
    sz = 1 if cube or len(cells) == 2 else 2
    return (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, sz)


def _corners(box):
    x0, y0, sx, sy, sz = box
    return [(x0 + sx * (i & 1), y0 + sy * (i >> 1 & 1), sz * (i >> 2 & 1)) for i in range(8)]


def _rot(p, pivot, d, th):
    """Rotate p by th about the horizontal axis through ``pivot`` perpendicular to direction d."""
    rx, ry = p[0] - pivot[0], p[1] - pivot[1]
    along = rx * d[0] + ry * d[1]
    c, s = math.cos(th), math.sin(th)
    a2, z2 = along * c + p[2] * s, -along * s + p[2] * c
    return (pivot[0] + rx - along * d[0] + a2 * d[0], pivot[1] + ry - along * d[1] + a2 * d[1], z2)


def _rolled(box, d, th):
    pts = _corners(box)
    a = max(p[0] * d[0] + p[1] * d[1] for p in pts)       # the leading bottom edge is the pivot
    return [_rot(p, (a * d[0], a * d[1]), d, th) for p in pts]


def rolls_to(start, d, end):
    """True if rolling ``start`` a quarter turn towards d gives exactly the box ``end``."""
    pts = _rolled(start, d, math.pi / 2)
    lo = [min(p[i] for p in pts) for i in range(3)]
    size = [max(p[i] for p in pts) - lo[i] for i in range(3)]
    got = (lo[0], lo[1], size[0], size[1], size[2])
    return lo[2] > -1e-6 and all(abs(a - b) < 1e-6 for a, b in zip(got, end))


def rolled_box(start, d):
    """The box a quarter roll towards d ends up as, whether or not the board is there to hold it."""
    pts = _rolled(start, d, math.pi / 2)
    lo = [min(p[i] for p in pts) for i in range(3)]
    size = [max(p[i] for p in pts) - lo[i] for i in range(3)]
    return (round(lo[0]), round(lo[1]), round(size[0]), round(size[1]), round(size[2]))


def start_roll(start, d, idx, now):
    return SimpleNamespace(box=start, d=d, idx=idx, t0=now)


def progress(anim, now):
    return min(1.0, (now - anim.t0) / ROLL_MS)


def _hull(points):
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts
    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2 and ((out[-1][0] - out[-2][0]) * (p[1] - out[-2][1])
                                     - (out[-1][1] - out[-2][1]) * (p[0] - out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    return half(pts) + half(pts[::-1])


def draw_box(surf, box, origin, sq, roll=None, scale=1.0, ring=False):
    """Draw ``box``; ``roll`` = (direction, angle) draws it part-way through a roll."""
    x0, y0, sx, sy, sz = box
    if scale != 1.0:
        cx, cy = x0 + sx / 2, y0 + sy / 2
        sx, sy, sz = sx * scale, sy * scale, sz * scale
        x0, y0 = cx - sx / 2, cy - sy / 2
    box = (x0, y0, sx, sy, sz)
    longs = [k for k, size in enumerate((sx, sy, sz)) if abs(size - 2 * scale) < 1e-6]
    long_axis = longs[0] if len(longs) == 1 else None
    pts = _rolled(box, *roll) if roll else _corners(box)
    proj = lambda p: (origin[0] + p[0] * sq, origin[1] + p[1] * sq - p[2] * sq * TILT)

    ground = _hull([proj((p[0] + 0.45 * p[2], p[1] - 0.18 * p[2], 0)) for p in pts])   # soft shadow
    if len(ground) >= 3:
        xs, ys = [g[0] for g in ground], [g[1] for g in ground]
        rect = pygame.Rect(int(min(xs)) - 2, int(min(ys)) - 2, int(max(xs) - min(xs)) + 4, int(max(ys) - min(ys)) + 4)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.polygon(layer, (0, 0, 0, 70), [(gx - rect.x, gy - rect.y) for gx, gy in ground])
        surf.blit(layer, rect.topleft)

    for normal, idx in FACES:
        n = _rot(normal, (0, 0), *roll) if roll else normal
        if n[1] * TILT + n[2] <= 0.02:                      # faces away from the camera
            continue
        shade = max(0.42, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2])
        color = tuple(min(255, int(c * shade * 1.3)) for c in BASE)
        poly = [proj(pts[i]) for i in idx]
        pygame.draw.polygon(surf, color, poly)
        pygame.draw.polygon(surf, OUTLINE, poly, 2)
        seam = [(i, j) for i, j in zip(idx, idx[1:] + idx[:1]) if long_axis is not None and i ^ j == 1 << long_axis]
        if len(seam) == 2:                                   # the joint between the block's two cubes
            (a, b), (c, d) = seam
            mid = lambda i, j: tuple((u + v) / 2 for u, v in zip(proj(pts[i]), proj(pts[j])))
            pygame.draw.line(surf, tuple(int(k * 0.55) for k in color), mid(a, b), mid(c, d), 2)
        if ring and n[2] > 0.9:
            pygame.draw.polygon(surf, RING, poly, 4)
