"""Merge the street bin's body and lid (tools/blender_bin.py) into one player model for the 1 x 1 x 2 block.

    Blender -b -P tools/blender_bin_block.py -- BINDIR [HEIGHT] [DIAMETER]

Writes BINDIR/bin_block.glb: centred on its middle, HEIGHT tall (default 2) and DIAMETER across (default 0.94)
so it fills the block exactly whether it stands on one cell or lies across two (the bin is stretched a little).
"""
import json
import os
import sys

import bpy
from mathutils import Vector

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
lid = parts[1]
x, y_up, z = info['lid']                      # game coords (y up, z towards the camera) -> blender (x, -z, y)
lid.location = Vector((x, -z, y_up))
for o in parts:
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
obj = bpy.context.active_object
pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
lo = Vector([min(p[i] for p in pts) for i in range(3)])
hi = Vector([max(p[i] for p in pts) for i in range(3)])
mid = (lo + hi) / 2
obj.data.transform(__import__('mathutils').Matrix.Translation(-mid))
obj.scale = (W / max(hi.x - lo.x, hi.y - lo.y), W / max(hi.x - lo.x, hi.y - lo.y), H / (hi.z - lo.z))
bpy.ops.object.transform_apply(location=True, scale=True)


def colour_mat(name, rgb):
    """A flat colour as a 4x4 texture: the game's renderer lights glTF textures properly (see blender_bin.py)."""
    img = bpy.data.images.new(name, 4, 4)
    img.pixels = list(rgb) * 16
    img.pack()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = img
    nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.6
    b.inputs['Emission Color'].default_value = (0, 0, 0, 1)
    return m


def blob(name, loc, scale, rgb):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    o.data.materials.append(colour_mat(name, rgb))
    bpy.ops.object.transform_apply(scale=True)
    return o


R = W / 2 + 0.005                                                   # a face on the -Y side, a third of the way up
faces = [blob('eye_l', (-0.15, -R + 0.03, 0.36), (0.11, 0.05, 0.14), (0.92, 0.92, 0.9, 1)),
         blob('eye_r', (0.15, -R + 0.03, 0.36), (0.11, 0.05, 0.14), (0.92, 0.92, 0.9, 1)),
         blob('pupil_l', (-0.14, -R - 0.005, 0.34), (0.05, 0.03, 0.07), (0.02, 0.02, 0.03, 1)),
         blob('pupil_r', (0.16, -R - 0.005, 0.34), (0.05, 0.03, 0.07), (0.02, 0.02, 0.03, 1)),
         blob('mouth', (0, -R + 0.02, 0.12), (0.17, 0.035, 0.05), (0.03, 0.03, 0.04, 1))]
bpy.ops.object.select_all(action='DESELECT')
for o in faces + [obj]:
    o.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.join()
obj = bpy.context.active_object
print('BLOCK', tuple(round(v, 2) for v in obj.dimensions))
bpy.ops.export_scene.gltf(filepath=os.path.join(DIR, 'bin_block.glb'), export_format='GLB', use_selection=True,
                          export_image_format='JPEG', export_jpeg_quality=70)
