"""Bake a skinned, animated cat out of a Unity data.unity3d into one OBJ per frame (Zoomies by Scarlet Games).

    python tools/unity_cat.py DATA.unity3d CAT_NAME OUTDIR CLIP:FRAMES [CLIP:FRAMES ...]

CAT_NAME is the GameObject of the SkinnedMeshRenderer (e.g. Cat_Siamese). For each CLIP (e.g. 'Arm_Cat|Run_F')
FRAMES poses are sampled evenly over its length, the skeleton is posed from the clip (Mecanim streamed, dense and
constant curves decoded here), the mesh is skinned on the CPU and written as OUTDIR/<clip>_<n>.obj together with
OUTDIR/<texture>.png and OUTDIR/index.json ({obj name: texture}). Positions keep Unity's axes, x mirrored like
UnityPy's own OBJ export, so tools/blender_zb.py (pivot mode) converts them like any other mesh.
"""
import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler

data, cat, out, *clips = sys.argv[1:]
out = Path(out)
out.mkdir(parents=True, exist_ok=True)
env = UnityPy.load(data)

smr = None
for o in env.objects:
    if o.type.name == 'SkinnedMeshRenderer':
        d = o.read()
        if d.m_GameObject.read().m_Name == cat:
            smr = d
            break
assert smr, 'no skinned mesh named ' + cat
mesh = smr.m_Mesh.read()
h = MeshHandler(mesh)
h.process()
verts = np.array(h.m_Vertices, dtype=np.float64).reshape(-1, 3)
uvs = np.array(h.m_UV0, dtype=np.float64).reshape(-1, 2)
bw = np.array(h.m_BoneWeights, dtype=np.float64).reshape(-1, 4)
bi = np.array(h.m_BoneIndices, dtype=np.int64).reshape(-1, 4)
raw_index = np.array(list(h.m_IndexBuffer), dtype=np.int64)
if raw_index.max() > 255 or len(raw_index) * 2 == len(mesh.m_IndexBuffer) * 1 and False:
    index = raw_index                                         # the handler already unpacked the indices
else:
    index = np.frombuffer(bytes(raw_index.astype(np.uint8)), dtype='<u2' if h.m_Use16BitIndices else '<u4')
subs = mesh.m_SubMeshes
tris = []
step = 2 if h.m_Use16BitIndices else 4
for sm in subs:
    first = sm.firstByte // step if len(index) * step == len(mesh.m_IndexBuffer) else sm.firstByte // step
    tris.append(index[first:first + sm.indexCount])
tris = np.concatenate(tris).reshape(-1, 3)


def mat(m):
    return np.array([[m.e00, m.e01, m.e02, m.e03], [m.e10, m.e11, m.e12, m.e13],
                     [m.e20, m.e21, m.e22, m.e23], [m.e30, m.e31, m.e32, m.e33]], dtype=np.float64)


bind = [mat(m) for m in mesh.m_BindPose]
bones = [b.read() for b in smr.m_Bones]


# ---- the skeleton: every transform from the bones up to the root ----
class Node:
    def __init__(self, tr):
        self.tr = tr
        self.name = tr.m_GameObject.read().m_Name
        self.parent = None
        self.t = np.array([tr.m_LocalPosition.x, tr.m_LocalPosition.y, tr.m_LocalPosition.z])
        q = tr.m_LocalRotation
        self.q = np.array([q.x, q.y, q.z, q.w])
        self.s = np.array([tr.m_LocalScale.x, tr.m_LocalScale.y, tr.m_LocalScale.z])


nodes = {}


def node(tr):
    k = tr.object_reader.path_id
    if k not in nodes:
        n = Node(tr)
        nodes[k] = n
        if tr.m_Father.path_id:
            n.parent = node(tr.m_Father.read())
    return nodes[k]


bone_nodes = [node(b) for b in bones]
root = bone_nodes[0]
while root.parent:
    root = root.parent
ALL = list(nodes.values())


def path_of(n, top):
    parts = []
    while n is not top and n is not None:
        parts.append(n.name)
        n = n.parent
    return '/'.join(reversed(parts))


def quat_mat(q):
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def local(n, pose):
    t, q, s = pose.get(n, (n.t, n.q, n.s))
    m = np.eye(4)
    m[:3, :3] = quat_mat(q) * s[None, :]
    m[:3, 3] = t
    return m


def world(n, pose, cache):
    if n in cache:
        return cache[n]
    m = local(n, pose)
    cache[n] = world(n.parent, pose, cache) @ m if n.parent else m
    return cache[n]


# ---- clips ----
def bindings_of(clip):
    res = []
    i = 0
    for b in clip.m_ClipBindingConstant.genericBindings:
        cnt = {1: 3, 2: 4, 3: 3, 4: 3}.get(b.attribute, 1) if b.typeID == 4 else 1
        res.append((i, cnt, b))
        i += cnt
    return res


def decode(clip):
    """-> (length, curves) where curves[index] = callable(t) -> float, for every Mecanim curve."""
    mc = clip.m_MuscleClip
    c = mc.m_Clip.data
    words = list(c.m_StreamedClip.data)
    raw = struct.pack('<%dI' % len(words), *words)
    streamed = {}
    p = 0
    while p + 8 <= len(raw):
        time, n = struct.unpack_from('<fi', raw, p)
        p += 8
        for _ in range(n):
            idx, a, b, cc, d = struct.unpack_from('<Iffff', raw, p)
            p += 20
            streamed.setdefault(idx, []).append((time, a, b, cc, d))
    ns = c.m_StreamedClip.curveCount
    dense = c.m_DenseClip
    nd = dense.m_CurveCount
    samples = np.array(dense.m_SampleArray, dtype=np.float64)
    const = list(c.m_ConstantClip.data)

    def curve(i):
        if i < ns:
            keys = streamed.get(i, [])

            def f(t):
                k = None
                for kk in keys:
                    if kk[0] <= t + 1e-9:
                        k = kk
                    else:
                        break
                if k is None:
                    return keys[0][4] if keys else 0.0
                dt = t - k[0]
                return ((k[1] * dt + k[2]) * dt + k[3]) * dt + k[4]
            return f
        if i < ns + nd:
            j = i - ns
            fc, sr = dense.m_FrameCount, dense.m_SampleRate

            def f(t):
                x = min(max(t * sr, 0.0), fc - 1)
                a = int(math.floor(x))
                b = min(a + 1, fc - 1)
                return samples[a * nd + j] * (1 - (x - a)) + samples[b * nd + j] * (x - a)
            return f
        v = const[i - ns - nd]
        return lambda t: v
    return mc.m_StopTime, curve


clipobjs = {}
for o in env.objects:
    if o.type.name == 'AnimationClip':
        d = o.read()
        clipobjs[d.m_Name] = d

# which ancestor do the clip's paths start from?
hashes = {}
best = None
for cand in [root] + [n for n in ALL if n.parent is None]:
    pass
first = clipobjs[clips[0].split(':')[0]]
want = {b.path for _, _, b in bindings_of(first) if b.typeID == 4}
for cand in ALL:
    hs = {zlib.crc32(path_of(n, cand).encode()) for n in ALL if n is not cand and cand in chain if False} if False else None
anc = []
n = bone_nodes[0]
while n:
    anc.append(n)
    n = n.parent
scores = []
for top in anc:
    m = {}
    for n in ALL:
        # n must lie below top
        x, below = n, False
        while x:
            if x is top:
                below = True
                break
            x = x.parent
        if below and n is not top:
            m[zlib.crc32(path_of(n, top).encode()) & 0xFFFFFFFF] = n
    scores.append((len(want & set(m)), top, m))
score, top, hmap = max(scores, key=lambda s: s[0])
print('animator root', top.name, 'matched', score, 'of', len(want))

mat_name = smr.m_Materials[0].read()
tex = None
for k, t in (mat_name.m_SavedProperties.m_TexEnvs.items() if isinstance(mat_name.m_SavedProperties.m_TexEnvs, dict)
             else mat_name.m_SavedProperties.m_TexEnvs):
    if str(k) in ('_MainTex', '_BaseMap') and t.m_Texture.path_id:
        tex = t.m_Texture.read()
        break
import os                                              # TEXTURE=Cat_White swaps the skin (the meshes share one UV layout)
if os.environ.get('TEXTURE'):
    for o in env.objects:
        if o.type.name == 'Texture2D':
            t = o.read()
            if t.m_Name == os.environ['TEXTURE']:
                tex = t
                break
if tex:
    img = tex.image.convert('RGBA')                 # a flat palette: a small nearest-neighbour copy is enough
    img.resize((128, 128), 0).save(out / (tex.m_Name + '.png'))
index_json = {}


def pose_at(clip, curves, t):
    pose = {}
    for i, cnt, b in bindings_of(clip):
        if b.typeID != 4 or (b.path & 0xFFFFFFFF) not in hmap:
            continue
        n = hmap[b.path & 0xFFFFFFFF]
        tt, qq, ss = pose.get(n, (n.t, n.q, n.s))
        vals = [curves(i + k)(t) for k in range(cnt)]
        if b.attribute == 1:
            tt = np.array(vals)
        elif b.attribute == 2:
            qq = np.array(vals)
        elif b.attribute == 3:
            ss = np.array(vals)
        pose[n] = (tt, qq, ss)
    return pose


bind_inv_ok = True
for spec in clips:
    cname, frames = spec.rsplit(':', 1)
    clip = clipobjs[cname]
    have = {b.path & 0xFFFFFFFF for _, _, b in bindings_of(clip) if b.typeID == 4}
    print(cname, 'bone paths matched', len(have & set(hmap)), 'of', len(have))
    length, curves = decode(clip)
    safe = re.sub(r'[^A-Za-z0-9]+', '_', cname).strip('_')
    for f in range(int(frames)):
        t = length * f / int(frames)
        cache = {}
        pose = pose_at(clip, curves, t)
        to_local = np.linalg.inv(world(top, pose, cache))        # the prefab sits somewhere in its scene: undo that
        skin = [to_local @ world(bn, pose, cache) @ bind[k] for k, bn in enumerate(bone_nodes)]
        S = np.stack(skin)                                    # (bones, 4, 4)
        vh = np.concatenate([verts, np.ones((len(verts), 1))], axis=1)
        pos = np.zeros((len(verts), 3))
        for k in range(4):
            M = S[bi[:, k]]                                   # (verts, 4, 4)
            pos += bw[:, k:k + 1] * np.einsum('vij,vj->vi', M, vh)[:, :3]
        if f == 0:
            centre0 = pos[:, [0, 2]].mean(axis=0)                  # keep every frame over the same spot: no root-motion drift
        pos[:, [0, 2]] -= pos[:, [0, 2]].mean(axis=0) - centre0
        name = '%s_%02d' % (safe, f)
        with open(out / (name + '.obj'), 'w') as fo:
            for x, y, z in pos:
                fo.write('v %.5f %.5f %.5f\n' % (-x, y, z))
            for u, v in uvs:
                fo.write('vt %.5f %.5f\n' % (u, v))
            for a, b, c in tris:
                fo.write('f %d/%d %d/%d %d/%d\n' % (a + 1, a + 1, c + 1, c + 1, b + 1, b + 1))
        index_json[name] = tex.m_Name if tex else None
    print(cname, frames, 'frames, length %.2fs' % length)
json.dump(index_json, open(out / 'index.json', 'w'), indent=1)
