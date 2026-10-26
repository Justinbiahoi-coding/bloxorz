"""Import a character FBX, fit it into the 1 x 1 x 2 block, attach its diffuse texture and export a .glb.
Also renders a preview PNG next to the output.

    Blender -b -P tools/blender_import_character.py -- IN.fbx DIFFUSE.png OUT.glb
"""
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
FBX, DIFFUSE, OUT = args
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.name.startswith('WGT')]   # skip rig widgets
for o in bpy.context.scene.objects:                 # drop armatures/empties, keep the meshes
    if o.type != 'MESH':
        o.select_set(False)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
for o in meshes:                                    # one UV layer with the same name, so join keeps the mapping
    uvs = o.data.uv_layers
    keep = uvs.active or (uvs[0] if len(uvs) else None)
    for layer in [l for l in uvs if l != keep]:
        uvs.remove(layer)
    if keep:
        keep.name = 'UVMap'
    print('UV', o.name, [l.name for l in o.data.uv_layers])
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.active_object
for o in list(bpy.context.scene.objects):
    if o is not obj:
        bpy.data.objects.remove(o, do_unlink=True)

pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
size = hi - lo
print('original size', tuple(round(v, 3) for v in size))
k = min(2.0 / size.z, 0.96 / max(size.x, size.y))   # tall axis -> 2 units, footprint within one cell
obj.location = -(lo + hi) / 2 * k
obj.scale = (k, k, k)
bpy.ops.object.transform_apply(location=True, scale=True)

# keep the FBX's own flat-colour materials (the baked diffuse uses a different UV set); no metal look
for m in obj.data.materials:
    if m and m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
        m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.0
        print('MAT', m.name, tuple(round(c, 2) for c in m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value))
bpy.ops.object.shade_smooth()
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True)
print('exported', OUT)

# quick preview render, camera in front (-Y) and a bit above
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in
                                                               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 600, 600
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
scene.collection.objects.link(cam)
cam.location = (2.2, -4.2, 1.6)
cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
scene.collection.objects.link(sun)
sun.rotation_euler = (0.8, 0.2, 0.6)
scene.render.filepath = OUT.replace('.glb', '_preview.png')
bpy.ops.render.render(write_still=True)
print('preview', scene.render.filepath)
