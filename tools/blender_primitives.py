"""Lit-ready primitives for the 3D view (Ursina's built-in cube/sphere have no normals, so lights do nothing).

    Blender -b -P tools/blender_primitives.py -- OUTDIR

box.glb   1 x 1 x 1 centred, slightly bevelled edges, every face mapped to the whole texture
ball.glb  sphere of diameter 1
cyl.glb   cylinder of diameter 1 and height 1, centred
"""
import os
import sys

import bpy

OUT = sys.argv[sys.argv.index('--') + 1]
os.makedirs(OUT, exist_ok=True)


def export(name):
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    if hasattr(bpy.ops.object, 'shade_auto_smooth'):
        try:
            bpy.ops.object.shade_auto_smooth(angle=0.6)
        except Exception:
            pass
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
    o.data.materials.append(mat)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', use_selection=True)
    bpy.data.objects.remove(o, do_unlink=True)
    print('exported', name)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.bevel(offset=0.035, segments=2)
bpy.ops.uv.reset()                               # each face spans the full texture
bpy.ops.object.mode_set(mode='OBJECT')
export('box')
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, segments=32, ring_count=16)
export('ball')
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=1)
export('cyl')
