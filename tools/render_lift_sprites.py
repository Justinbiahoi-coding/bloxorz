"""Render the pixel sprites the lift cutscene needs from our own 3D models (run from Source/ with its venv).

    cd Source && .venv/bin/python ../tools/render_lift_sprites.py

For the street bin (models/bin/bin_block.glb): the whole bin, the body alone and the lid alone, on one
canvas so they line up. For the cat (ui3d/cat.py): six sitting frames facing us and eight run frames facing left and right. Everything is drawn with the
same camera (so one scale), keyed off magenta, shrunk to 60 px tall, posterised and outlined. Output goes to
assets/textures/elev/.
"""
import builtins
import os
import sys

from panda3d.core import Filename
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'Source'))
os.chdir(os.path.join(HERE, '..', 'Source'))
from ui3d.world import ASSETS, aim_sun, configure, lights, point_camera           # noqa: E402

configure()
from ursina import Entity, Ursina, application, camera, color, Vec3, window       # noqa: E402

app = Ursina(title='sprites', fullscreen=False, size=(600, 700), development_mode=False)
application.asset_folder = ASSETS
Entity.default_shader = None
sun = lights(builtins.render)
window.color = color.rgb(255, 0, 255)
camera.fov = 12
camera.position = Vec3(0, 1.45, -13)
point_camera(camera, Vec3(0, 1.0, 0))
aim_sun(sun, Vec3(0, 1, 0))
OUT = os.path.join(ASSETS, 'textures', 'elev')
os.makedirs(OUT, exist_ok=True)
SHRINK = 8.5                                                                       # 512 px of render -> 60 px


def shoot():
    for _ in range(3):
        app.step()
    path = '/tmp/_lift_shot.png'
    base.win.saveScreenshot(Filename(path))
    im = Image.open(path).convert('RGBA')
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if r > 190 and g < 90 and b > 190:
                px[x, y] = (0, 0, 0, 0)
    return im


def finish(frames, names):
    """Crop every frame to the union box, shrink, posterise, outline and save."""
    boxes = [f.getbbox() for f in frames if f.getbbox()]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    for im, name in zip(frames, names):
        c = im.crop(box)
        sm = c.resize((max(1, round(c.width / SHRINK)), max(1, round(c.height / SHRINK))), Image.BOX)
        alpha = sm.split()[3].point(lambda v: 255 if v > 110 else 0)
        rgb = sm.convert('RGB').point(lambda v: min(255, (v // 28) * 28 + 22))
        spr = Image.merge('RGBA', (*rgb.split(), alpha))
        canvas = Image.new('RGBA', (spr.width + 2, spr.height + 2), (0, 0, 0, 0))
        canvas.alpha_composite(spr, (1, 1))
        ap, out = canvas.split()[3].load(), canvas.copy()
        op = out.load()
        for y in range(canvas.height):
            for x in range(canvas.width):
                if ap[x, y] == 0 and any(0 <= x + dx < canvas.width and 0 <= y + dy < canvas.height and ap[x + dx, y + dy]
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    op[x, y] = (20, 24, 40, 255)
        out.save(os.path.join(OUT, name + '.png'))
    print('saved', len(names), 'sprites', out.size)


# ---- the bin: whole, body, lid (same canvas via one shared box) ----
from ursina import destroy                                                         # noqa: E402


def bin_part(*names):
    holder = Entity(y=1.0)
    for n in names:
        e = Entity(parent=holder, model='models/bin/' + n)
        for m in e.findAllMaterials():
            m.setMetallic(0)
    return holder


shots = []
for names in (('bin_block',), ('bin_block_body',), ('bin_block_lid',)):
    h = bin_part(*names)
    shots.append(shoot())
    destroy(h)
finish(shots, ['bin', 'bin_body', 'bin_lid'])

# ---- the cat (Zoomies): run cycle facing right and left, sitting facing us ----
from ui3d.cat import Cat                                                           # noqa: E402
SPR_CAT = 3.2                                                                      # about 25 px tall: a cat, not a dog
cat = Cat(scale=SPR_CAT)
frames, names = [], []
for yaw, tag, kind, n in ((35, 'sit', 'Pet_sit', 6), (270, 'run_r', 'Run_F', 8), (90, 'run_l', 'Run_F', 8)):
    cat.root.rotation_y = yaw
    for i in range(n):
        cat.show(kind, i)
        frames.append(shoot())
        names.append('cat_%s_%d' % (tag, i))
finish(frames, names)
print('ok')
os._exit(0)
