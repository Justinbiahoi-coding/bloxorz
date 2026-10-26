"""Convert the voxel zombies (MagicaVoxel .obj) into game-sized .glb parts the game animates itself.

    Blender -b -P tools/blender_zombie.py -- SRCDIR OUTDIR

Each Zed_N.obj is imported (its .mtl points at the wrong image name, so the texture is re-linked by
number), scaled so the zombie is ZOMBIE_H cells tall standing on y=0 and centred on x/z, then cut into
five rigid parts by height and width: head, torso, arm_l, arm_r, legs. Each part's origin sits at its
joint (neck / shoulders / hips) so the game can rotate it there. Exported as OUTDIR/zed<N>_<part>.glb
plus OUTDIR/zombie_rig.json with the joint positions in game units (y up, z towards the camera).
"""
import json
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

SRC, OUT = sys.argv[sys.argv.index('--') + 1:]
os.makedirs(OUT, exist_ok=True)
ZOMBIE_H = 2.0                    # cells: the same height as the standing player block
HEAD = 0.84                       # fractions of the height: above this is the head,
SHOULDER = 0.80                   # arms hang from here,
HIP = 0.46                        # below this are the legs
ARM = 0.27                        # a face this far out from the centre (fraction of width) is an arm


def part_of(co, size, lo):
    """Which part a face belongs to, from its place in the model's own box. Arms are tested first: they
    hang past the hips, so testing height first would leave the forearms behind with the legs."""
    h = (co.z - lo.z) / size.z
    x = (co.x - lo.x) / size.x - 0.5
    if h > HEAD:
        return 'head'
    if h < SHOULDER and abs(x) > ARM:
        return 'arm_l' if x < 0 else 'arm_r'
    return 'legs' if h < HIP else 'torso'


rig = {}
for n in range(1, 7):
    obj_path = os.path.join(SRC, 'Zed_%d.obj' % n)
    if not os.path.exists(obj_path):
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=obj_path)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object

    for img in bpy.data.images:                       # the .mtl names the wrong file (Z-0-Zed_1.png)
        if not img.has_data:
            path = os.path.join(SRC, 'Zed_%d.png' % n)
            if os.path.exists(path):
                img.filepath = path
                img.reload()
    for mat in bpy.data.materials:
        if mat.use_nodes and 'Principled BSDF' in mat.node_tree.nodes:
            p = mat.node_tree.nodes['Principled BSDF']
            p.inputs['Metallic'].default_value = 0.0
            p.inputs['Roughness'].default_value = 0.95
            for node in mat.node_tree.nodes:          # voxel art: keep the palette crisp
                if node.type == 'TEX_IMAGE':
                    node.interpolation = 'Closest'

    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    k = ZOMBIE_H / (hi.z - lo.z)
    obj.location = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)) * k
    obj.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=True, scale=True)
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    size = hi - lo

    groups = {}                                        # faces -> part, by the face's centre
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        groups.setdefault(part_of(f.calc_center_median(), size, lo), []).append(f.index)
    bm.free()

    joints = {'head': (0, lo.z + size.z * HEAD, 0), 'torso': (0, lo.z + size.z * HIP, 0),
              'legs': (0, lo.z + size.z * HIP, 0),
              'arm_l': (-size.x * 0.34, lo.z + size.z * SHOULDER, 0),
              'arm_r': (size.x * 0.34, lo.z + size.z * SHOULDER, 0)}
    base = obj
    for part, faces in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        copy = base.copy()
        copy.data = base.data.copy()
        bpy.context.collection.objects.link(copy)
        bpy.context.view_layer.objects.active = copy
        copy.select_set(True)
        bm = bmesh.new()
        bm.from_mesh(copy.data)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in set(faces)], context='FACES')
        bm.to_mesh(copy.data)
        bm.free()
        jx, jy, jz = joints[part]
        copy.data.transform(Matrix.Translation((-jx, -jz, -jy)))   # origin at the joint (blender z up)
        copy.name = 'zed%d_%s' % (n, part)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, copy.name + '.glb'), export_format='GLB',
                                  use_selection=True, export_image_format='AUTO')
        bpy.data.objects.remove(copy, do_unlink=True)
    rig = {p: [j[0], j[1], j[2]] for p, j in joints.items()}       # blender (x, z, y) -> game (x, y, z)
    rig = {p: [j[0], j[1] - lo.z, -j[2]] for p, j in joints.items()}
    print('ZOMBIE', n, 'size', tuple(round(v, 2) for v in size), {p: len(f) for p, f in groups.items()})

with open(os.path.join(OUT, 'zombie_rig.json'), 'w') as f:
    json.dump({'height': ZOMBIE_H, 'joints': rig}, f, indent=1)
print('done')
