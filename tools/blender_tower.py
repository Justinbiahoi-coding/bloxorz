"""Build the tower for the 3D intro in Blender and export it as a glTF binary.

    /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender_tower.py -- W D H STOREYS OUT.glb

A dark concrete shaft with a slab band at every storey, framed and slightly recessed windows (a few lit,
warm), corner pilasters, a plinth with a lit glass entrance and canopy at the bottom, and a cornice on top.
Origin: centre of the base. Blender is Z-up; the glTF exporter turns that into Y-up.
"""
import random
import sys

import bpy

args = sys.argv[sys.argv.index('--') + 1:]
W, D, H, STOREYS, OUT = float(args[0]), float(args[1]), float(args[2]), int(args[3]), args[4]
rng = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, emit=0.0, rough=0.85, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if emit:
        p.inputs['Emission Color'].default_value = (*rgb, 1)
        p.inputs['Emission Strength'].default_value = emit
    return m


MAT = {
    'concrete': material('concrete', (0.25, 0.26, 0.31)),
    'band': material('band', (0.36, 0.37, 0.42)),
    'frame': material('frame', (0.07, 0.07, 0.09)),
    'glass': material('glass', (0.03, 0.045, 0.08), rough=0.25),
    'lit': material('lit', (0.85, 0.42, 0.12), emit=0.55),
    'door': material('door', (1.0, 0.78, 0.45), emit=2.2),
}
parts = {k: [] for k in MAT}


def box(kind, cx, cy, cz, sx, sy, sz):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.active_object
    o.scale = (sx, sy, sz)
    parts[kind].append(o)


storey = (H - 2.0) / STOREYS                       # leave room for plinth and cornice
plinth = 2.0
box('concrete', 0, 0, H / 2, W, D, H)              # the shaft
box('band', 0, 0, plinth / 2, W + 0.5, D + 0.5, plinth)          # plinth
box('band', 0, 0, H - 0.25, W + 0.35, D + 0.35, 0.5)             # cornice
for sx in (-1, 1):                                  # corner pilasters
    for sy in (-1, 1):
        box('band', sx * (W / 2 - 0.15), sy * (D / 2 - 0.15), H / 2, 0.42, 0.42, H)

faces = [((0, -1), W), ((0, 1), W), ((-1, 0), D), ((1, 0), D)]     # (normal, face width)
for s in range(STOREYS):
    z0 = plinth + s * storey
    box('band', 0, 0, z0 + 0.06, W + 0.18, D + 0.18, 0.12)       # slab edge at each storey
    for (nx, ny), width in faces:
        n = max(2, round(width / 1.7))
        step = (width - 0.9) / n
        for i in range(n):
            u = -width / 2 + 0.45 + step * (i + 0.5)
            ww, wh = step * 0.62, storey * 0.55
            zc = z0 + storey * 0.52
            off = (W / 2 if nx else D / 2)
            px, py = (nx * off, u) if nx else (u, ny * off)
            # frame (slightly proud), glass (recessed), sill
            fx, fy = (0.06, ww + 0.12) if nx else (ww + 0.12, 0.06)
            box('frame', px + nx * 0.01, py + ny * 0.01, zc, fx, fy, wh + 0.12)
            gx, gy = (0.05, ww) if nx else (ww, 0.05)
            box('lit' if rng.random() < 0.13 else 'glass', px + nx * 0.03, py + ny * 0.03, zc, gx, gy, wh)
            sx_, sy_ = (0.16, ww + 0.2) if nx else (ww + 0.2, 0.16)
            box('band', px + nx * 0.07, py + ny * 0.07, zc - wh / 2 - 0.05, sx_, sy_, 0.08)

# lit glass entrance and a canopy on the front (-Y) side
box('door', 0, -D / 2 - 0.03, 1.1, 2.4, 0.06, 1.9)
box('frame', 0, -D / 2 - 0.06, 1.1, 0.08, 0.08, 1.9)
box('band', 0, -D / 2 - 0.75, 2.25, 3.4, 1.5, 0.14)

for kind, objs in parts.items():                    # one mesh per material keeps the file small
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
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True)
print('exported', OUT)
