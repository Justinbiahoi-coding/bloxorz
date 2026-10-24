"""Dump where a Zombie Barricades scene places its meshes (permission: see docs, CREDITS).

    python tools/unity_scene.py DATA_DIR LEVEL OUT.json

Writes [{mesh, pos:[x,y,z], rot:[x,y,z] (Unity euler degrees), scale:[x,y,z], tex}] with world transforms
(parents resolved) for every MeshFilter+MeshRenderer in the scene, so the game can lay out the same streets.
"""
import json
import math
import sys

import UnityPy

data, level, out = sys.argv[1:]
env = UnityPy.load(data + '/' + level)


def quat_matrix(q):
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


cache = {}


def world(tr):
    """(R, pos, scale-diag) of a Transform, scale folded into R's columns on the way up."""
    key = tr.object_reader.path_id
    if key in cache:
        return cache[key]
    p, q, s = tr.m_LocalPosition, tr.m_LocalRotation, tr.m_LocalScale
    R = quat_matrix((q.x, q.y, q.z, q.w))
    L = [[R[i][j] * (s.x, s.y, s.z)[j] for j in range(3)] for i in range(3)]
    pos = [p.x, p.y, p.z]
    if tr.m_Father.path_id:
        PL, ppos = world(tr.m_Father.read())
        pos = [ppos[i] + sum(PL[i][j] * pos[j] for j in range(3)) for i in range(3)]
        L = mul(PL, L)
    cache[key] = (L, pos)
    return cache[key]


def decompose(L):
    sx, sy, sz = (math.sqrt(sum(L[i][j] ** 2 for i in range(3))) for j in range(3))
    R = [[L[i][j] / (sx, sy, sz)[j] for j in range(3)] for i in range(3)]
    # Unity euler (ZXY order): x = asin(-R[1][2]), y = atan2(R[0][2], R[2][2]), z = atan2(R[1][0], R[1][1])
    ex = math.degrees(math.asin(max(-1, min(1, -R[1][2]))))
    if abs(R[1][2]) < 0.9999:
        ey, ez = math.degrees(math.atan2(R[0][2], R[2][2])), math.degrees(math.atan2(R[1][0], R[1][1]))
    else:
        ey, ez = math.degrees(math.atan2(-R[2][0], R[0][0])), 0.0
    return [ex, ey, ez], [sx, sy, sz]


def tex_name(rend):
    for mp in rend.m_Materials:
        try:
            envs = mp.read().m_SavedProperties.m_TexEnvs
            for k, t in (envs.items() if isinstance(envs, dict) else envs):
                if str(k) == '_MainTex' and t.m_Texture.path_id:
                    return t.m_Texture.read().m_Name
        except Exception:
            pass


res = []
for o in env.objects:
    if o.type.name != 'MeshRenderer':
        continue
    try:
        r = o.read()
        go = r.m_GameObject.read()
        comps = [(c.component if hasattr(c, 'component') else c).read() for c in go.m_Components]
        mesh = next(c for c in comps if hasattr(c, 'm_Mesh')).m_Mesh.read().m_Name
        L, pos = world(go.m_Transform.read())
    except Exception:
        continue
    rot, scale = decompose(L)
    res.append({'mesh': mesh, 'pos': [round(v, 3) for v in pos], 'rot': [round(v, 2) for v in rot],
                'scale': [round(v, 3) for v in scale], 'tex': tex_name(r), 'active': go.m_IsActive})
json.dump(res, open(out, 'w'))
print(len(res), 'placements ->', out)
