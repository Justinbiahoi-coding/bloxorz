"""Build the tower for the 3D intro in Blender and export it as a glTF binary.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender_tower.py -- W D H STOREYS TEXDIR OUT.glb

A weathered concrete shaft (SDXL texture, cube-projected UVs) with a slab band at every storey, a dark
recessed groove down each corner, framed windows whose panes carry either a dark moonlit-glass image or a
warm lit-room image, a plinth with a lit entrance and canopy, and a cornice. Images come from TEXDIR
(concrete_wall.png, window_dark.png, window_lit.png) and are embedded in the .glb.
Origin: centre of the base. Blender is Z-up; the glTF exporter turns that into Y-up.
"""
import math
import os
import random
import sys

import bpy

args = sys.argv[sys.argv.index('--') + 1:]
W, D, H, STOREYS, TEX, OUT = float(args[0]), float(args[1]), float(args[2]), int(args[3]), args[4], args[5]
rng = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb=(1, 1, 1), image=None, emit=0.0, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    p = nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    if image and os.path.exists(os.path.join(TEX, image)):
        t = nodes.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(os.path.join(TEX, image))
        links.new(t.outputs['Color'], p.inputs['Base Color'])
        if emit:
            links.new(t.outputs['Color'], p.inputs['Emission Color'])
    elif emit:
        p.inputs['Emission Color'].default_value = (*rgb, 1)
    if emit:
        p.inputs['Emission Strength'].default_value = emit
    return m


MAT = {
    'concrete': material('concrete', image='concrete_wall.png'),
    'band': material('band', (0.15, 0.16, 0.20)),
    'groove': material('groove', (0.03, 0.03, 0.04)),
    'frame': material('frame', (0.10, 0.10, 0.12)),
    'glass': material('glass', (0.05, 0.07, 0.12), image='window_dark.png', rough=0.3),
    'lit': material('lit', (1.0, 0.84, 0.47), image='window_lit.png', emit=0.8),
    'door': material('door', (0.9, 0.6, 0.28), emit=0.45),
}
parts = {k: [] for k in MAT}


def box(kind, cx, cy, cz, sx, sy, sz):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.scale = (sx, sy, sz)
    parts[kind].append(o)


def pane(kind, cx, cy, cz, w, h, nx, ny):
    """A flat window pane facing (nx, ny), UVs covering the whole image."""
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.scale = (w, h, 1)
    o.rotation_euler = (math.pi / 2, 0, math.atan2(nx, -ny))
    parts[kind].append(o)


plinth = 2.0
storey = (H - plinth - 0.6) / STOREYS
box('concrete', 0, 0, H / 2, W, D, H)                              # the shaft
box('band', 0, 0, plinth / 2, W + 0.5, D + 0.5, plinth)           # plinth
box('band', 0, 0, H - 0.3, W + 0.4, D + 0.4, 0.6)                 # cornice
for sx in (-1, 1):                                                  # dark recessed groove down each corner
    for sy in (-1, 1):
        box('groove', sx * (W / 2 - 0.02), sy * (D / 2 - 0.02), H / 2, 0.26, 0.26, H - 0.2)

faces = [((0, -1), W), ((0, 1), W), ((-1, 0), D), ((1, 0), D)]   # (outward normal, face width)
for s in range(STOREYS):
    z0 = plinth + s * storey
    box('band', 0, 0, z0 + 0.08, W + 0.16, D + 0.16, 0.16)        # slab edge at each storey
    for (nx, ny), width in faces:
        n = max(2, round(width / 2.4))                             # few, large windows like a slender tower
        step = (width - 1.0) / n
        for i in range(n):
            u = -width / 2 + 0.5 + step * (i + 0.5)
            ww, wh = step * 0.55, storey * 0.58
            zc = z0 + storey * 0.55
            off = W / 2 if nx else D / 2
            px, py = (nx * off, u) if nx else (u, ny * off)
            fx, fy = (0.08, ww + 0.14) if nx else (ww + 0.14, 0.08)
            box('frame', px, py, zc, fx, fy, wh + 0.14)                                    # frame
            pane('lit' if rng.random() < 0.12 else 'glass', px + nx * 0.045, py + ny * 0.045, zc, ww, wh, nx, ny)
            sx_, sy_ = (0.18, ww + 0.22) if nx else (ww + 0.22, 0.18)
            box('band', px + nx * 0.06, py + ny * 0.06, zc - wh / 2 - 0.07, sx_, sy_, 0.08)  # sill

F = -D / 2 - 0.25                                                    # front face of the plinth
box('door', 0, F - 0.02, 1.0, 2.4, 0.04, 1.8)                       # lit glass entrance (front, -Y)
for x in (-1.25, 0, 1.25):                                          # its frame and mullion
    box('frame', x, F - 0.05, 1.0, 0.1, 0.08, 1.85)
box('frame', 0, F - 0.05, 1.95, 2.6, 0.08, 0.1)
box('band', 0, F - 0.75, 2.3, 3.6, 1.5, 0.14)                       # canopy
for x in (-1.6, 1.6):                                               # canopy posts
    box('frame', x, F - 1.4, 1.15, 0.08, 0.08, 2.3)

for kind, objs in parts.items():                                    # one mesh per material
    if not objs:
        continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = kind
    obj.data.materials.clear()
    obj.data.materials.append(MAT[kind])
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if kind == 'concrete':                                          # world-scale UVs for the wall texture
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.cube_project(cube_size=6.0)
        bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True)
print('exported', OUT)
