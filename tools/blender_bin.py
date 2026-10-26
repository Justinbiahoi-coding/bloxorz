"""Split the street bin (zfr_lowpoly_trashbin.glb) into a body and a lid the opening cutscene animates.

    Blender -b -P tools/blender_bin.py -- SRC.glb OUTDIR [SCALE]

The body stands on y=0 centred on x/z; the lid is exported around its own centre so it can tilt there, and its
resting position on the body is written to OUTDIR/bin.json (game units, y up).
"""
import json
import os
import sys

import bpy
from mathutils import Vector

SRC, OUT, *rest = sys.argv[sys.argv.index('--') + 1:]
K = float(rest[0]) if rest else 0.9
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
parts = {o.name.lower(): o for o in bpy.context.scene.objects if o.type == 'MESH'}
body, lid = parts['kova'], parts['kapak']
for o in (body, lid):
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw                       # keep the parent's scale
    if o is lid:
        o.rotation_euler = (0, 0, 0)          # the model is posed open on its hinge: shut it
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def box(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


PAINT = (0.50, 0.57, 0.55, 1.0)             # painted municipal steel; the 2K metal texture rendered black in game
for img in list(bpy.data.images):
    bpy.data.images.remove(img)
steel = bpy.data.images.new('steel', 4, 4)    # a flat 4x4 texture: the game's renderer only lights textured glTF right
steel.pixels = list(PAINT) * 16
steel.pack()
for o in (body, lid):
    for m in o.data.materials:
        nt = m.node_tree
        b = nt.nodes['Principled BSDF']
        for l in list(nt.links):
            if l.to_socket.name == 'Base Color':          # keep the BSDF -> output link
                nt.links.remove(l)
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = steel
        nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Metallic'].default_value = 0.0
        b.inputs['Emission Color'].default_value = (0, 0, 0, 1)   # the source has white emission at strength 0: Panda reads it as glowing
        b.inputs['Roughness'].default_value = 0.7
def lay_flat(o):
    """The lid mesh is modelled tilted open: turn it about x then y until its thin axis points up."""
    import math
    from mathutils import Euler
    best = (1e9, 0, 0)
    for ax in range(-180, 181, 3):
        for ay in range(-90, 91, 3):
            m = Euler((math.radians(ax), math.radians(ay), 0)).to_matrix()
            zs = [(m @ v.co).z for v in o.data.vertices]
            best = min(best, (max(zs) - min(zs), ax, ay))
    o.data.transform(Euler((math.radians(best[1]), math.radians(best[2]), 0)).to_matrix().to_4x4())


lay_flat(lid)
bpy.context.view_layer.update()
lo, hi = box(body)
llo, lhi = box(lid)
lid.location += Vector(((lo.x + hi.x) / 2 - (llo.x + lhi.x) / 2, (lo.y + hi.y) / 2 - (llo.y + lhi.y) / 2,
                        hi.z - 0.04 - llo.z))
bpy.ops.object.select_all(action='DESELECT')
lid.select_set(True)
bpy.context.view_layer.objects.active = lid
bpy.ops.object.transform_apply(location=True)       # bake the move into the mesh
print('DBG body', [round(v, 2) for v in (hi - lo)], 'lid', [round(v, 2) for v in (lhi - llo)])
base = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
llo, lhi = box(lid)
lid_c = Vector(((llo.x + lhi.x) / 2, (llo.y + lhi.y) / 2, (llo.z + lhi.z) / 2))
info = {'lid': [round(v * K, 4) for v in (lid_c.x - base.x, lid_c.z - base.z, -(lid_c.y - base.y))],   # blender -> game (x, y, z)
        'height': round((hi.z - lo.z) * K, 4), 'width': round((hi.x - lo.x) * K, 4)}
for o, origin in ((body, base), (lid, lid_c)):
    o.data.transform(__import__('mathutils').Matrix.Translation(-origin))
    o.location = (0, 0, 0)
    o.scale = (K, K, K)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, scale=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'bin_%s.glb' % ('body' if o is body else 'lid')),
                              export_format='GLB', use_selection=True,
                              export_image_format='JPEG', export_jpeg_quality=70)
json.dump(info, open(os.path.join(OUT, 'bin.json'), 'w'))
print('BIN', info)
