"""3D world plumbing shared by the 3D front-end: window setup, lights, model loading, coordinates.

Engine cell (x, y) sits at world (x, 0, -y): engine rows grow towards the camera's south.
Floors are stacked bottom-up: floor 0 is the lobby, the last one the rooftop; floor i stands at floor_y(i).
"""
from functools import lru_cache
from pathlib import Path

from panda3d.core import Filename, loadPrcFileData

ASSETS = Path(__file__).resolve().parent.parent / 'assets'
# Panda3D wants Unix-style paths; a raw Windows path (D:\...) fails to load
FONT = Filename.fromOsSpecific(str(ASSETS / 'fonts' / 'Fredoka.ttf')).getFullpath()
FLOOR_H = 6.0                 # storey height in world units (one cell = one unit)
FURNITURE = 1.25              # Kenney models are sized for ~0.8 unit rooms; scale them to our cells


def configure():
    """Before Ursina starts: OpenAL for the music (mp3 through ffmpeg), antialiasing."""
    loadPrcFileData('', 'audio-library-name p3openal_audio\nframebuffer-multisample 1\nmultisamples 4\n'
                        'sync-video 1\nwindow-title Bloxorz Tower')


def floor_y(index):
    return index * FLOOR_H


def cell_pos(x, y, base_y=0.0, h=0.0):
    from ursina import Vec3
    return Vec3(x, base_y + h, -y)


def lights(render):
    """Moonlight from above-left plus a cool fill and a warm lantern that follows the player.
    Note: Ursina runs Panda3D y-up, so light positions are plain Ursina coordinates. Built-in Ursina
    cubes have no normals; lit geometry uses models/prim/*.glb (tools/blender_primitives.py)."""
    from panda3d.core import AmbientLight, DirectionalLight, PointLight, Vec4
    sun = DirectionalLight('moon')
    sun.setColor(Vec4(1.05, 1.0, 1.1, 1))
    sun_np = render.attachNewNode(sun)
    render.setLight(sun_np)
    amb = AmbientLight('fill')
    amb.setColor(Vec4(0.46, 0.47, 0.56, 1))
    render.setLight(render.attachNewNode(amb))
    lamp = PointLight('lantern')
    lamp.setColor(Vec4(1.0, 0.78, 0.5, 1))
    lamp.setAttenuation((1, 0, 0.08))
    lamp_np = render.attachNewNode(lamp)
    render.setLight(lamp_np)
    sun_np.setPythonTag('lantern', lamp_np)
    sun_np.setPythonTag('ambient', render.find('**/fill'))
    # copies: getColor() is a live view, so later setColor calls would rewrite the stored levels too
    sun_np.setPythonTag('levels', (Vec4(sun.getColor()), Vec4(amb.getColor())))
    render.setShaderAuto()
    return sun_np


def set_exposure(sun_np, key=1.0, fill=1.0):
    """Scale the moon and the fill light; the cutscene runs brighter than the lit floors."""
    sun, amb = sun_np.getPythonTag('levels')
    sun_np.node().setColor(sun * key)
    amb_np = sun_np.getPythonTag('ambient')
    if not amb_np.isEmpty():
        amb_np.node().setColor(amb * fill)


def aim_sun(sun_np, target):
    """Moon over the floor being played (from above, left and a bit behind the camera)."""
    sun_np.setPos(target.x - 8, target.y + 16, target.z - 10)
    sun_np.lookAt(target.x, target.y, target.z)


def move_lantern(sun_np, pos):
    """The warm light pool rides above the player."""
    sun_np.getPythonTag('lantern').setPos(pos.x, pos.y + 2.6, pos.z - 0.6)


@lru_cache(maxsize=None)
def model_path(name):
    return str(ASSETS / 'models' / '{}.glb'.format(name))


@lru_cache(maxsize=None)
def texture_path(name):
    path = ASSETS / 'textures' / '{}.png'.format(name)
    return str(path) if path.exists() else None


def point_camera(cam, target):
    """Turn the camera towards ``target`` with yaw and pitch only (no roll), so it never ends up upside down
    when it swings from looking down at a floor to looking up a facade."""
    import math
    d = target - cam.position
    cam.rotation = (-math.degrees(math.atan2(d.y, math.hypot(d.x, d.z))), math.degrees(math.atan2(d.x, d.z)), 0)


def paint_by_height(np, low=(0.17, 0.19, 0.28), high=(0.86, 0.89, 0.97), snow_line=0.6, axis=1):
    """Give an untextured mesh (e.g. from Hunyuan3D) vertex colours: rock below the snow line, snow above.
    Heights are read from the raw vertex data; glTF files keep y as up there (axis=1)."""
    from panda3d.core import GeomVertexFormat, GeomVertexReader, GeomVertexWriter
    lo_z, hi_z = None, None
    geoms = [(node, i) for node in np.findAllMatches('**/+GeomNode') for i in range(node.node().getNumGeoms())]
    for node, i in geoms:                                   # find the height range first
        reader = GeomVertexReader(node.node().getGeom(i).getVertexData(), 'vertex')
        while not reader.isAtEnd():
            z = reader.getData3()[axis]
            lo_z = z if lo_z is None else min(lo_z, z)
            hi_z = z if hi_z is None else max(hi_z, z)
    span = max(1e-6, hi_z - lo_z)
    for node, i in geoms:
        geom = node.node().modifyGeom(i)
        vdata = geom.modifyVertexData()
        if not vdata.getFormat().hasColumn('color'):
            vdata.setFormat(GeomVertexFormat.getV3n3c4())
        reader, writer = GeomVertexReader(vdata, 'vertex'), GeomVertexWriter(vdata, 'color')
        while not reader.isAtEnd():
            k = (reader.getData3()[axis] - lo_z) / span
            t = min(1.0, max(0.0, (k - snow_line) / 0.08))     # short blend into the snow
            writer.setData4(*[a + (b - a) * t for a, b in zip(low, high)], 1.0)
    np.setMaterialOff(1)                                    # let the vertex colours show
