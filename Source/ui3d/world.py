"""3D world plumbing shared by the 3D front-end: window setup, lights, model loading, coordinates.

Engine cell (x, y) sits at world (x, 0, -y): engine rows grow towards the camera's south.
Floors are stacked: floor i of the tower has its ground at height floor_y(i).
"""
from functools import lru_cache
from pathlib import Path

from panda3d.core import loadPrcFileData

ASSETS = Path(__file__).resolve().parent.parent / 'assets'
FLOOR_H = 6.0                 # storey height in world units (one cell = one unit)
FURNITURE = 1.25              # Kenney models are sized for ~0.8 unit rooms; scale them to our cells


def configure():
    """Before Ursina starts: fullscreen at the desktop size, no audio library, antialiasing."""
    loadPrcFileData('', 'audio-library-name null\nframebuffer-multisample 1\nmultisamples 4\n'
                        'sync-video 1\nwindow-title Bloxorz Tower')


def floor_y(index):
    return -index * FLOOR_H


def cell_pos(x, y, base_y=0.0, h=0.0):
    from ursina import Vec3
    return Vec3(x, base_y + h, -y)


def lights(render):
    """A warm key light that casts shadows plus a cool fill; Panda3D's shader generator does the shading
    (works on macOS' OpenGL 2.1, unlike Ursina's GLSL 1.50 shaders)."""
    from panda3d.core import AmbientLight, DirectionalLight, Vec4
    sun = DirectionalLight('sun')
    sun.setColor(Vec4(1.15, 1.08, 0.98, 1))
    sun.setShadowCaster(True, 2048, 2048)
    lens = sun.getLens()
    lens.setFilmSize(40, 40)
    lens.setNearFar(1, 120)
    sun_np = render.attachNewNode(sun)
    render.setLight(sun_np)
    amb = AmbientLight('fill')
    amb.setColor(Vec4(0.62, 0.62, 0.68, 1))
    render.setLight(render.attachNewNode(amb))
    render.setShaderAuto()
    return sun_np


def aim_sun(sun_np, target):
    """Keep the shadow camera over the floor being played (Ursina's x, y, z are Panda's x, z, y)."""
    sun_np.setPos(target.x - 7, target.z - 9, target.y + 20)
    sun_np.lookAt(target.x, target.z, target.y)


@lru_cache(maxsize=None)
def model_path(name):
    return str(ASSETS / 'models' / '{}.glb'.format(name))


@lru_cache(maxsize=None)
def texture_path(name):
    path = ASSETS / 'textures' / '{}.png'.format(name)
    return str(path) if path.exists() else None
