"""Export chosen meshes (+ their main texture) from the installed Zombie Barricades game data.

    python tools/unity_extract.py DATA_DIR OUT_DIR REGEX [REGEX ...]

DATA_DIR is the game's `Zombie Barricades_Data`. For every mesh whose name matches a REGEX that is used by
a MeshFilter + MeshRenderer, writes OUT_DIR/<mesh>.obj (with UVs) and OUT_DIR/<texture>.png, plus
OUT_DIR/index.json {mesh: texture}. Used with Barricade Entertainment's permission (see docs/CREDITS.md);
the extracted files are converted by tools/blender_zb.py and the raw output is never committed.
"""
import json
import re
import sys
from pathlib import Path

import UnityPy

data, out, *pats = sys.argv[1:]
out = Path(out)
out.mkdir(parents=True, exist_ok=True)
want = [re.compile(p) for p in pats]
env = UnityPy.load(data)
index, done = {}, set()


def components(go):
    for c in go.m_Components:
        yield (c.component if hasattr(c, 'component') else c).read()


def main_texture(renderer):
    for mp in renderer.m_Materials:
        try:
            envs = mp.read().m_SavedProperties.m_TexEnvs
            for k, t in (envs.items() if isinstance(envs, dict) else envs):
                if str(k) == '_MainTex' and t.m_Texture.path_id:
                    return t.m_Texture.read()
        except Exception:
            pass


for o in env.objects:
    if o.type.name != 'MeshRenderer':
        continue
    try:
        r = o.read()
        comps = list(components(r.m_GameObject.read()))
        mesh = next(c for c in comps if hasattr(c, 'm_Mesh')).m_Mesh.read()
    except Exception:
        continue
    name = mesh.m_Name
    if name in done or not any(p.search(name) for p in want):
        continue
    tex = main_texture(r)
    try:
        (out / (name + '.obj')).write_text(mesh.export())
        if tex:
            tex.image.save(out / (tex.m_Name + '.png'))
        index[name] = tex.m_Name if tex else None
        done.add(name)
    except Exception as e:
        print('skip', name, e)
(out / 'index.json').write_text(json.dumps(index, indent=1))
print(len(index), 'meshes ->', out)
