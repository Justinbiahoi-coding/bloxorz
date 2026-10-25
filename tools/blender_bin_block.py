"""Merge the street bin's body and lid (tools/blender_bin.py) into one player model for the 1 x 1 x 2 block.

    Blender -b -P tools/blender_bin_block.py -- BINDIR [HEIGHT] [DIAMETER]

Writes BINDIR/bin_block.glb: centred on its middle, HEIGHT tall (default 2) and DIAMETER across (default 0.94)
so it fills the block exactly whether it stands on one cell or lies across two (the bin is stretched a little).
Also writes bin_block_body.glb and bin_block_lid.glb with the very same transform, for the lift cutscene.
"""
import json
import os
import sys

import bpy
from mathutils import Matrix, Vector

DIR, *rest = sys.argv[sys.argv.index('--') + 1:]
H = float(rest[0]) if rest else 2.0
W = float(rest[1]) if len(rest) > 1 else 0.94
info = json.load(open(os.path.join(DIR, 'bin.json')))
bpy.ops.wm.read_factory_settings(use_empty=True)
parts = []
for name in ('bin_body', 'bin_lid'):
    bpy.ops.import_scene.gltf(filepath=os.path.join(DIR, name + '.glb'))
    for o in bpy.context.selected_objects:
        if o.type == 'MESH':
            parts.append(o)
for o in parts:
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw
body, lid = parts
x, y_up, z = info['lid']                      # game coords (y up, z towards the camera) -> blender (x, -z, y)
lid.location = Vector((x, -z, y_up))
for o in parts:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
pts = [o.matrix_world @ Vector(c) for o in parts for c in o.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
mid = (lo + hi) / 2
sx = W / max(hi.x - lo.x, hi.y - lo.y)
sz = H / (hi.z - lo.z)
for o in parts:
    o.data.transform(Matrix.Translation(-mid))
    o.data.transform(Matrix.Diagonal((sx, sx, sz, 1.0)))


def export(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(DIR, name + '.glb'), export_format='GLB', use_selection=True,
                              export_image_format='JPEG', export_jpeg_quality=70)


export([body], 'bin_block_body')
export([lid], 'bin_block_lid')
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
print('BLOCK', tuple(round(v, 2) for v in bpy.context.active_object.dimensions))
export([bpy.context.active_object], 'bin_block')
