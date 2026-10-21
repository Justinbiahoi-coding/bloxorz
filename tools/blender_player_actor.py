"""Turn the rigged Trash Can character (Mattt_L, CC BY-NC-SA) into an animated glTF for the game.

    Blender -b -P tools/blender_player_actor.py -- IN.fbx OUT.glb [PREVIEW_DIR]

* drops the camera dolly rig and its widgets
* rigid parts that hang off control bones (shoes, gloves, head, lid, body) are re-bound to the matching
  deform bone, so only the DEF-* skeleton is needed and every part follows it
* actions, all on the DEF bones and sampled per frame:
    guard        the artist's boxing pose (feet one in front of the other: the one-cell stance)
    guard_wide   boxing pose with the legs spread sideways, one foot on each of two cells
    guard_lunge  boxing pose with a deep front/back split across two cells in line
    run          the artist's run cycle
* exported with only the deform bones; preview renders of each action go to PREVIEW_DIR if given
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index('--') + 1:]
FBX, OUT = args[0], args[1]
PREVIEW = args[2] if len(args) > 2 else None
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
for o in list(bpy.context.scene.objects):
    if o.name.startswith('WGT') or o.name == 'Dolly_Rig':
        bpy.data.objects.remove(o, do_unlink=True)
rig = bpy.data.objects['rig.001']

REBIND = {'foot_tweak': 'DEF-foot', 'hand_tweak': 'DEF-hand', 'upper_arm_tweak': 'DEF-upper_arm',
          'head': 'DEF-spine.006', 'tweak_spine.005': 'DEF-spine.005', 'tweak_spine.003': 'DEF-spine.003'}
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    if o.parent_type != 'BONE':
        continue
    bone = o.parent_bone
    base, _, side = bone.partition('.')
    target = REBIND.get(bone) or (REBIND.get(base, '') + ('.' + side if side else ''))
    mw = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = mw
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    g = o.vertex_groups.new(name=target)
    g.add([v.index for v in o.data.vertices], 1.0, 'REPLACE')
    mod = o.modifiers.new('Armature', 'ARMATURE')
    mod.object = rig
    o.parent = rig
    o.matrix_parent_inverse = rig.matrix_world.inverted()
    print('rebound', o.name, bone, '->', target)

for m in bpy.data.materials:                     # flat matte colours, no metal
    if m.use_nodes and 'Principled BSDF' in m.node_tree.nodes:
        m.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.0

scene = bpy.context.scene
pb = rig.pose.bones
DEF = [b.name for b in rig.data.bones if b.name.startswith('DEF')]
src_guard = bpy.data.actions['rig.001|Boxing_Pose']
src_run = bpy.data.actions['rig.001|run_cycle']


def bake(name, source, frames, deltas=None):
    """Sample ``source`` on the DEF bones into a new action, applying extra local rotations (degrees)."""
    rig.animation_data.action = source
    poses = []
    for f in frames:
        scene.frame_set(f)
        poses.append({n: (pb[n].location.copy(), pb[n].rotation_quaternion.copy() if pb[n].rotation_mode == 'QUATERNION'
                          else pb[n].rotation_euler.to_quaternion(), pb[n].scale.copy()) for n in DEF})
    act = bpy.data.actions.new(name)
    rig.animation_data.action = act
    for i, pose in enumerate(poses):
        for n, (loc, rot, scl) in pose.items():
            p = pb[n]
            p.rotation_mode = 'QUATERNION'
            if deltas and n in deltas:
                rot = rot @ Euler([math.radians(a) for a in deltas[n]], 'XYZ').to_quaternion()
            p.location, p.rotation_quaternion, p.scale = loc, rot, scl
            for path in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(path, frame=i + 1)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, len(frames)
    act.use_fake_user = True
    print('baked', name, len(frames))
    return act


def fcurves(act):
    """F-curves of an action, for both the old flat and the Blender 4.4+ layered action layout."""
    if hasattr(act, 'layers') and act.layers:
        return [fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    return list(getattr(act, 'fcurves', []))


# Stances by IK: an IK constraint on each leg pulls the ankle (DEF-shin.*.001 tail) to a target, the knee
# pointing forward (-Y, the way the boxer faces); the hips drop a little so wide feet can reach the floor.
# Feet positions are relative to the pelvis, in Blender units (one game cell = 1 / CELL_K units).
CELL_K = 2.0 / 2.279
HALF = 0.5 / CELL_K                              # half a cell
ANKLE_Z = 0.24
STANCES = {                                      # (left foot, right foot, hip drop)
    'guard': ((0.16, -0.20), (-0.16, 0.22), 0.0),              # one cell: front / back
    'guard_wide': ((HALF, 0.06), (-HALF, 0.06), 0.15),          # two cells across the facing
    'guard_lunge': ((0.12, -HALF), (-0.12, HALF), 0.15),        # two cells in line
}
rig.animation_data.action = src_guard
scene.frame_set(64)
pelvis = rig.matrix_world @ pb['DEF-spine'].head
targets, poles = {}, {}
for side in 'LR':
    for kind, store in (('ik', targets), ('pole', poles)):
        e = bpy.data.objects.new('%s_%s' % (kind, side), None)
        scene.collection.objects.link(e)
        store[side] = e
    c = pb['DEF-shin.%s.001' % side].constraints.new('IK')
    c.target, c.pole_target, c.chain_count = targets[side], poles[side], 4
    c.pole_angle = math.radians(-90)
    foot = pb['DEF-foot.' + side]                 # keep each shoe flat, turned as in the artist's pose
    targets[side].rotation_mode = 'QUATERNION'
    targets[side].rotation_quaternion = (rig.matrix_world @ foot.matrix).to_quaternion()
    cr = foot.constraints.new('COPY_ROTATION')
    cr.target = targets[side]
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='POSE')
def bake_stance(fl, fr, drop, offs):
    """Bake the boxing pose with the feet pinned by IK while the whole rig is ``drop`` lower, so the legs
    bend to reach; the game lowers the character by the same amount for this stance. ``offs`` corrects
    each IK target so the shoe (DEF-foot) lands where wanted."""
    rig.delta_location.z = -drop                 # (the action keys the object location itself)
    want = {}
    for side, (fx, fy) in (('L', fl), ('R', fr)):
        want[side] = Vector((pelvis.x + fx, pelvis.y + fy, GROUND - drop))   # floor, as seen while lowered
        targets[side].location = want[side] + offs[side]
        poles[side].location = (pelvis.x + fx * 1.1, pelvis.y + fy - 2.0, 0.6 - drop)
    rig.animation_data.action = src_guard
    bpy.context.view_layer.update()
    bpy.ops.nla.bake(frame_start=24, frame_end=128, step=2, only_selected=False, visual_keying=True,
                     clear_constraints=False, use_current_action=False, bake_types={'POSE'})
    baked = rig.animation_data.action
    cons = [pb['DEF-shin.%s.001' % sd].constraints[0] for sd in 'LR'] + \
        [pb['DEF-foot.' + sd].constraints[0] for sd in 'LR']
    for c in cons:
        c.mute = True                            # measure the baked pose itself
    rig.animation_data.action = baked
    scene.frame_set(20)
    bpy.context.view_layer.update()
    feet = {sd: (rig.matrix_world @ pb['DEF-foot.' + sd].head).copy() for sd in 'LR'}
    for c in cons:
        c.mute = False
    rig.delta_location.z = 0
    return baked, {sd: want[sd] - feet[sd] for sd in 'LR'}


import json
GROUND = 0.25                                    # shoe-on-floor height of DEF-foot in the artist's pose
DROPS = {'guard': 0.0, 'guard_wide': 0.17, 'guard_lunge': 0.27}
drops = {}
for name, (fl, fr, _) in STANCES.items():
    offs = {'L': Vector(), 'R': Vector()}
    for it in range(3):                          # correct the IK targets until the shoes land on the spots
        baked, err = bake_stance(fl, fr, DROPS[name], offs)
        worst = max(e.length for e in err.values())
        print('stance', name, it, 'error', round(worst, 3))
        if worst < 0.03 or it == 2:
            break
        for sd in 'LR':
            offs[sd] = offs[sd] + err[sd]
        bpy.data.actions.remove(baked)
    baked.name = name
    baked.use_fake_user = True
    drops[name] = DROPS[name] * CELL_K           # in game units
    print('baked', name)
bpy.ops.object.mode_set(mode='OBJECT')
for side in 'LR':
    for bone in ('DEF-shin.%s.001' % side, 'DEF-foot.' + side):
        con = pb[bone].constraints
        for c in list(con):
            con.remove(c)
bake('run', src_run, range(6, 127, 2))
for a in list(bpy.data.actions):                 # only our four go into the file
    if a.name not in ('guard', 'guard_wide', 'guard_lunge', 'run'):
        bpy.data.actions.remove(a)

for name in ('guard', 'guard_wide', 'guard_lunge'):        # report where the feet end up
    rig.animation_data.action = bpy.data.actions[name]
    scene.frame_set(20)
    fl, fr = (rig.matrix_world @ pb['DEF-foot.' + s].head for s in 'LR')
    hd = rig.matrix_world @ pb['DEF-spine.006'].head
    drops[name] = max(0.0, ((fl.z + fr.z) / 2 - GROUND) * CELL_K)    # game units to lower this stance by
    print('FEET', name, 'L', tuple(round(v, 2) for v in fl), 'R', tuple(round(v, 2) for v in fr),
          'head', tuple(round(v, 2) for v in hd))
with open(OUT.replace('.glb', '_stances.json'), 'w') as f:
    json.dump(drops, f)
if PREVIEW:
    os.makedirs(PREVIEW, exist_ok=True)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'MATERIAL'
    scene.render.resolution_x = scene.render.resolution_y = 320
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    scene.camera = cam
    for name in ('guard', 'guard_wide', 'guard_lunge', 'run'):
        rig.animation_data.action = bpy.data.actions[name]
        for f in (1, 20):
            scene.frame_set(f)
            for view, loc in (('front', (0, -6, 1.2)), ('side', (6, 0, 1.2))):
                cam.location = loc
                cam.rotation_euler = (Vector((0, 0, 0.9)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
                scene.render.filepath = os.path.join(PREVIEW, '%s_%02d_%s.png' % (name, f, view))
                bpy.ops.render.render(write_still=True)

rig.animation_data.action = bpy.data.actions['guard']
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_animations=True,
                          export_animation_mode='ACTIONS', export_def_bones=True, export_force_sampling=True,
                          export_apply=False)
print('exported', OUT)
