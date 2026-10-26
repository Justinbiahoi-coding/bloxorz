"""Convert Majadroid's Low Poly Apocalyptic Buildings (CC0) into game-sized .glb files.

    Blender -b -P tools/blender_apoc.py -- SRCDIR OUTDIR

SRCDIR is the pack's folder (it holds `fbx files/` and `textures/`). Each fbx is imported, its textures
are re-linked from SRCDIR/textures, it is scaled so one Blender unit becomes one game cell (the pack is
modelled at ~1 unit = 1 m, a storey is ~3.4 units; our cells are 1 unit and a storey is 6), centred on
x/z with its feet at y=0, and exported as OUTDIR/<name>.glb with the images packed in.
"""
import os
import sys

import bpy
from mathutils import Vector

SRC, OUT = sys.argv[sys.argv.index('--') + 1:]
WANT = ('building-01', 'building-02', 'building-05', 'building-07', 'wreckage-3-types',
        'billboards-4-types', 'fire-stairs')          # a varied few: the whole pack is far too heavy
TEX_PX = 256                                          # the 1K source textures are embedded in every file
os.makedirs(OUT, exist_ok=True)
FBX = os.path.join(SRC, 'fbx files')
TEX = os.path.join(SRC, 'textures')
SCALE = 0.42                      # pack metres -> our cells (a cell is roughly 2.4 m of building)


def relink_textures():
    """The fbx files reference textures by bare name; point them at the pack's folder and pack them in."""
    for img in bpy.data.images:
        if img.source != 'FILE':
            continue
        if not img.has_data:                          # the fbx files reference textures by bare name
            path = os.path.join(TEX, os.path.basename(img.filepath.replace('\\', '/')))
            if os.path.exists(path):
                img.filepath = path
                img.reload()
        if img.has_data and max(img.size) > TEX_PX:   # shrink: each .glb carries its own copy
            img.scale(TEX_PX, TEX_PX)
            img.pack()
    for mat in bpy.data.materials:                        # matte, no metal (we light the scene ourselves)
        if mat.use_nodes and 'Principled BSDF' in mat.node_tree.nodes:
            p = mat.node_tree.nodes['Principled BSDF']
            p.inputs['Metallic'].default_value = 0.0
            p.inputs['Roughness'].default_value = 0.9


for fbx in sorted(f for f in os.listdir(FBX) if f.endswith('.fbx') and os.path.splitext(f)[0] in WANT):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(FBX, fbx))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    obj.location = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) * SCALE
    obj.scale = (SCALE, SCALE, SCALE)
    bpy.ops.object.transform_apply(location=True, scale=True)
    relink_textures()
    name = os.path.splitext(fbx)[0]
    size = (hi - lo) * SCALE
    print('CONVERTED', name, tuple(round(v, 1) for v in size), len(obj.data.polygons), 'tris')
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=70)
print('done')
