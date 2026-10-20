"""Model the player character, a cute metal trash can, in Blender and export it as a glTF binary.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender_trashcan.py -- TEXDIR OUT.glb

Fits the 1 x 1 x 2 block: 2 units tall, about 0.94 wide, origin at its centre, long axis Blender Z
(glTF Y). Galvanised body with ribs, a base rim, a domed lid with a handle, two side handles, and a face
(SDXL sticker, TEXDIR/face.png with alpha) wrapped on the front (-Y) of the body.
"""
import math
import os
import sys

import bmesh
import bpy

args = sys.argv[sys.argv.index('--') + 1:]
TEX, OUT = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)

H, R = 2.0, 0.44                          # total height, body radius at the top
BOT = -H / 2


def material(name, rgb=(1, 1, 1), image=None, rough=0.5, metal=0.0, alpha=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    p = nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    path = os.path.join(TEX, image) if image else None
    if path and os.path.exists(path):
        t = nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(path)
        links.new(t.outputs['Color'], p.inputs['Base Color'])
        if alpha:
            links.new(t.outputs['Alpha'], p.inputs['Alpha'])
            m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m


METAL = material('metal', (1.0, 1.0, 1.0), image='metal.png', rough=0.4)
DARK = material('dark', (0.5, 0.53, 0.58), rough=0.5)
FACE = material('face', image='face.png', rough=0.6, alpha=True)


def finish(obj, mat, smooth=True):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    if smooth:
        bpy.ops.object.shade_smooth()
    return obj


def cylinder(r1, r2, z0, z1, mat, verts=40):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=z1 - z0,
                                    location=(0, 0, (z0 + z1) / 2))
    return finish(bpy.context.active_object, mat)


def ring(r, z, thick, mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=thick, location=(0, 0, z),
                                     major_segments=48, minor_segments=10)
    return finish(bpy.context.active_object, mat)


body_top = BOT + 1.72
r_bottom = R * 0.9
cylinder(r_bottom, R, BOT + 0.05, body_top, METAL)                      # slightly tapered body
ring(r_bottom + 0.01, BOT + 0.07, 0.035, DARK)                          # base rim
for k in (0.28, 0.5, 0.72):                                             # pressed ribs
    z = BOT + 0.05 + (body_top - BOT - 0.05) * k
    ring(r_bottom + (R - r_bottom) * k + 0.004, z, 0.02, METAL)
ring(R + 0.012, body_top, 0.03, DARK)                                   # top rim
cylinder(R + 0.04, R + 0.02, body_top, body_top + 0.07, METAL)          # lid skirt
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=40, ring_count=20, location=(0, 0, body_top + 0.07))
lid = bpy.context.active_object
lid.scale = (R + 0.02, R + 0.02, 0.16)
bpy.ops.object.transform_apply(scale=True)
bm = bmesh.new()                                                        # keep only the upper dome
bm.from_mesh(lid.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context='VERTS')
bm.to_mesh(lid.data)
bm.free()
finish(lid, METAL)
bpy.ops.mesh.primitive_torus_add(major_radius=0.13, minor_radius=0.03,   # lid handle (a half loop)
                                 location=(0, 0, body_top + 0.21), rotation=(math.pi / 2, 0, 0))
finish(bpy.context.active_object, DARK)
for side in (-1, 1):                                                    # side handles
    bpy.ops.mesh.primitive_torus_add(major_radius=0.1, minor_radius=0.022,
                                     location=(side * (R + 0.02), 0, body_top - 0.18), rotation=(0, math.pi / 2, 0))
    finish(bpy.context.active_object, DARK)

# the face: a band of a slightly larger cone over the front, UVs spanning the sticker image
face_mesh = bpy.data.meshes.new('face')
bm = bmesh.new()
uv = bm.loops.layers.uv.new()
a0, a1, seg = math.radians(-58), math.radians(58), 16
z0, z1 = BOT + 0.45, BOT + 1.62
cols = []
for i in range(seg + 1):
    a = a0 + (a1 - a0) * i / seg
    col = []
    for z in (z0, z1):
        t = (z - BOT - 0.05) / (body_top - BOT - 0.05)
        r = r_bottom + (R - r_bottom) * t + 0.006
        col.append(bm.verts.new((math.sin(a) * r, -math.cos(a) * r, z)))
    cols.append(col)
for i in range(seg):
    f = bm.faces.new((cols[i][0], cols[i + 1][0], cols[i + 1][1], cols[i][1]))
    for loop, (u, v) in zip(f.loops, ((i / seg, 0), ((i + 1) / seg, 0), ((i + 1) / seg, 1), (i / seg, 1))):
        loop[uv].uv = (u, v)
bm.to_mesh(face_mesh)
bm.free()
face = bpy.data.objects.new('face', face_mesh)
bpy.context.collection.objects.link(face)
bpy.context.view_layer.objects.active = face
face.select_set(True)
finish(face, FACE)

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True)
print('exported', OUT)
