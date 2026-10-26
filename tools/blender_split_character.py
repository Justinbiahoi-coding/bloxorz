"""Split the trash-can character FBX into rigid parts for procedural animation and export each as a .glb.

    Blender -b -P tools/blender_split_character.py -- IN.fbx OUTDIR

Parts (by mesh, left/right by x): body (can, lid, eyes, brows), leg_l / leg_r (leg + shoe), arm_l / arm_r
(arm + shoulder + glove). The whole character is scaled so it stands 2 units tall with its feet at y=0
and centred on x/z. Each part's origin is moved to its joint (hip / shoulder / body centre) so it can be
rotated there; the joint positions go to OUTDIR/player_rig.json. Blender is Z-up, the files are Y-up.
"""
import json
import os
import sys

import bpy
from mathutils import Vector

FBX, OUT = sys.argv[sys.argv.index('--') + 1:]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.startswith('WGT')]
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o not in meshes:
        bpy.data.objects.remove(o, do_unlink=True)


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)]))


lo, hi = bounds(meshes)
k = 2.0 / (hi.z - lo.z)
centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
for o in meshes:                                  # scale about the feet centre, feet at z = 0
    o.location = (o.location - centre) * k
    o.scale = (k, k, k)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=True, scale=True)


def mats(o):
    return {m.name for m in o.data.materials if m}


groups = {'body': [], 'leg_l': [], 'leg_r': [], 'arm_l': [], 'arm_r': []}
for o in meshes:
    m = mats(o)
    (b0, b1) = bounds([o])
    side = 'l' if (b0.x + b1.x) / 2 < 0 else 'r'
    if m & {'Shoe', 'Sole'} or (m == {'Arms'} and b1.z < 1.0):
        groups['leg_' + side].append(o)              # shoes, and the lower (leg) cylinders
    elif m & {'Gloves', 'Shoulder', 'Arms'}:
        groups['arm_' + side].append(o)
    else:
        groups['body'].append(o)

rig = {}
for name, objs in groups.items():
    b0, b1 = bounds(objs)
    if name.startswith('leg'):
        joint = Vector(((b0.x + b1.x) / 2, (b0.y + b1.y) / 2, b1.z))      # hip: top of the leg
    elif name.startswith('arm'):
        joint = Vector(((b0.x + b1.x) / 2, (b0.y + b1.y) / 2, b1.z - 0.05))  # shoulder
    else:
        joint = Vector((0, 0, b0.z))                                       # body: its lowest point
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = name
    obj.data.transform(__import__('mathutils').Matrix.Translation(-joint))
    obj.location = (0, 0, 0)
    for m in obj.data.materials:
        if m and m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
            m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.0
    bpy.ops.object.shade_smooth()
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'player_%s.glb' % name), export_format='GLB',
                              use_selection=True)
    # Blender (x, y, z) -> glTF/Ursina (x, z, -y)
    rig[name] = {'joint': [joint.x, joint.z, -joint.y], 'size': [b1.x - b0.x, b1.z - b0.z, b1.y - b0.y]}
    print('part', name, len(objs), 'joint', tuple(round(v, 3) for v in rig[name]['joint']))

with open(os.path.join(OUT, 'player_rig.json'), 'w') as f:
    json.dump(rig, f, indent=1)
print('done')
