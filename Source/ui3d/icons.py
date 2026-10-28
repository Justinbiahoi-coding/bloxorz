"""Small flat icons drawn as meshes, for glyphs Fredoka does not have.

Each function builds the icon in a unit box (about -0.5..0.5) and scales it to ``size``.
"""
import math

from ursina import Entity, Mesh, Vec3


def _shape(parent, points, triangles, size, col, colors=None, **kw):
    mesh = Mesh(vertices=[Vec3(x, y, 0) for x, y in points], triangles=triangles, mode='triangle',
                colors=colors)
    e = Entity(parent=parent, model=mesh, scale=size, color=col, **kw)
    e.double_sided = True          # strokes wind either way
    return e


def _stroke(points, width):
    """Quads along a polyline: returns (vertices, triangles)."""
    verts, tris = [], []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy) or 1
        ox, oy = -dy / n * width / 2, dx / n * width / 2
        i = len(verts)
        verts += [(x0 + ox, y0 + oy), (x1 + ox, y1 + oy), (x1 - ox, y1 - oy), (x0 - ox, y0 - oy)]
        tris += [(i, i + 1, i + 2), (i, i + 2, i + 3)]
    return verts, tris


def _arc(cx, cy, r, a0, a1, steps=18):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / steps)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / steps))) for k in range(steps + 1)]


def triangle(parent, size, col, angle=0, **kw):
    """A solid triangle pointing right (angle 0), up (-90), left (180) or down (90)."""
    e = _shape(parent, [(-.4, -.45), (.5, 0), (-.4, .45)], [(0, 1, 2)], size, col, **kw)
    e.rotation_z = angle
    return e


ARROW_ANGLES = {'up': -90, 'down': 90, 'left': 180, 'right': 0}


def arrow(parent, size, col, direction='right', **kw):
    return triangle(parent, size, col, ARROW_ANGLES[direction], **kw)


def pause(parent, size, col, **kw):
    pts = [(-.38, -.42), (-.12, -.42), (-.12, .42), (-.38, .42),
           (.12, -.42), (.38, -.42), (.38, .42), (.12, .42)]
    return _shape(parent, pts, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)], size, col, **kw)


def square(parent, size, col, **kw):
    pts = [(-.38, -.38), (.38, -.38), (.38, .38), (-.38, .38)]
    return _shape(parent, pts, [(0, 1, 2), (0, 2, 3)], size, col, **kw)


def step(parent, size, col, backwards=False, **kw):
    """Triangle against a bar: skip forward (or back)."""
    pts = [(-.45, -.42), (.2, 0), (-.45, .42), (.22, -.45), (.42, -.45), (.42, .45), (.22, .45)]
    e = _shape(parent, pts, [(0, 1, 2), (3, 4, 5), (3, 5, 6)], size, col, **kw)
    if backwards:
        e.rotation_z = 180
    return e


def check(parent, size, col, **kw):
    verts, tris = _stroke([(-.4, 0), (-.12, -.3), (.42, .32)], .16)
    return _shape(parent, verts, tris, size, col, **kw)


def lock(parent, size, col, **kw):
    """Padlock: a body and a shackle."""
    body = [(-.36, -.45), (.36, -.45), (.36, .08), (-.36, .08)]
    verts, tris = list(body), [(0, 1, 2), (0, 2, 3)]
    sv, st = _stroke([(-.22, .08)] + _arc(0, .22, .22, 180, 0) + [(.22, .08)], .12)
    k = len(verts)
    verts += sv
    tris += [(a + k, b + k, c + k) for a, b, c in st]
    return _shape(parent, verts, tris, size, col, **kw)


def restart(parent, size, col, **kw):
    """A circular arrow."""
    pts = _arc(0, 0, .34, 60, 340)
    verts, tris = _stroke(pts, .13)
    ex, ey = pts[0]
    k = len(verts)
    verts += [(ex - .2, ey + .02), (ex + .14, ey + .2), (ex + .12, ey - .18)]
    tris += [(k, k + 1, k + 2)]
    return _shape(parent, verts, tris, size, col, **kw)


def chevron(parent, size, col, direction='left', **kw):
    verts, tris = _stroke([(.18, .38), (-.2, 0), (.18, -.38)], .14)
    e = _shape(parent, verts, tris, size, col, **kw)
    e.rotation_z = {'left': 0, 'right': 180, 'up': 90, 'down': -90}[direction]
    return e


def cube(parent, size, col, **kw):
    """An isometric block, the player's piece: three faces in three shades."""
    top = [(0, .46), (.4, .24), (0, .02), (-.4, .24)]
    left = [(-.4, .24), (0, .02), (0, -.46), (-.4, -.24)]
    right = [(0, .02), (.4, .24), (.4, -.24), (0, -.46)]
    verts = top + left + right
    tris = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (8, 9, 10), (8, 10, 11)]
    shades = [1.0] * 4 + [.62] * 4 + [.8] * 4
    colors = [(s, s, s, 1) for s in shades]
    return _shape(parent, verts, tris, size, col, colors=colors, **kw)


def gear(parent, size, col, teeth=8, **kw):
    verts, tris = [(0, 0)], []
    steps = teeth * 4
    for k in range(steps + 1):
        a = 2 * math.pi * k / steps
        r = .46 if (k % 4) in (1, 2) else .34
        verts.append((r * math.cos(a), r * math.sin(a)))
        if k:
            tris.append((0, k, k + 1))
    return _shape(parent, verts, tris, size, col, **kw)
