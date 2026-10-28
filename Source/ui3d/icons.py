"""Small flat icons drawn as meshes, for glyphs Fredoka does not have (arrows, play, pause, square)."""
from ursina import Entity, Mesh, Vec3


def _shape(parent, points, triangles, size, col, **kw):
    mesh = Mesh(vertices=[Vec3(x, y, 0) for x, y in points], triangles=triangles, mode='triangle')
    return Entity(parent=parent, model=mesh, scale=size, color=col, **kw)


def triangle(parent, size, col, angle=0, **kw):
    """A solid triangle pointing right (angle 0), up (-90), left (180) or down (90)."""
    e = _shape(parent, [(-.4, -.45), (.5, 0), (-.4, .45)], [(0, 1, 2)], size, col, **kw)
    e.rotation_z = angle
    return e


def pause(parent, size, col, **kw):
    pts = [(-.4, -.45), (-.12, -.45), (-.12, .45), (-.4, .45),
           (.12, -.45), (.4, -.45), (.4, .45), (.12, .45)]
    return _shape(parent, pts, [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7)], size, col, **kw)


def square(parent, size, col, **kw):
    pts = [(-.4, -.4), (.4, -.4), (.4, .4), (-.4, .4)]
    return _shape(parent, pts, [(0, 1, 2), (0, 2, 3)], size, col, **kw)


def step(parent, size, col, backwards=False, **kw):
    """Triangle against a bar: skip forward (or back)."""
    pts = [(-.45, -.42), (.2, 0), (-.45, .42), (.22, -.45), (.42, -.45), (.42, .45), (.22, .45)]
    e = _shape(parent, pts, [(0, 1, 2), (3, 4, 5), (3, 5, 6)], size, col, **kw)
    if backwards:
        e.rotation_z = 180
    return e


ARROW_ANGLES = {'up': -90, 'down': 90, 'left': 180, 'right': 0}


def arrow(parent, size, col, direction='right', **kw):
    """A chevron-like arrow head for key hints."""
    return triangle(parent, size, col, ARROW_ANGLES[direction], **kw)
