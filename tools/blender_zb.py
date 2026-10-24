"""Convert meshes exported by tools/unity_extract.py into game-sized .glb files.

    Blender -b -P tools/blender_zb.py -- SRCDIR OUTDIR [SCALE]

Each SRCDIR/<name>.obj gets SRCDIR/<texture>.png (named in index.json) as a crisp, matte palette material,
is scaled by SCALE (metres -> our cells, default 0.42 like blender_apoc.py), centred on x/z with its feet at
y=0, and written to OUTDIR/<name>.glb. UnityPy's OBJ export already matches Blender's handedness, so no mirroring.
"""
import json
import os
import sys

import bpy
from mathutils import Vector

SRC, OUT, *rest = sys.argv[sys.argv.index('--') + 1:]
SCALE = float(rest[0]) if rest else 0.42
os.makedirs(OUT, exist_ok=True)
index = json.load(open(os.path.join(SRC, 'index.json')))

for name, tex in sorted(index.items()):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=os.path.join(SRC, name + '.obj'), forward_axis='NEGATIVE_Z', up_axis='Y')
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not objs:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.95
    if tex and os.path.exists(os.path.join(SRC, tex + '.png')):
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(os.path.join(SRC, tex + '.png'))
        node.interpolation = 'Closest'
        mat.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    obj.location = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) * SCALE
    obj.scale = (SCALE, SCALE, SCALE)
    bpy.ops.object.transform_apply(location=True, scale=True)
    print('CONVERTED', name, tuple(round(v, 1) for v in (hi - lo) * SCALE))
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', export_apply=True)
print('done')
