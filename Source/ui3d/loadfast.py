"""Faster model lookups, and a hook so the loading bar can move while a scene is being built.

Ursina 5.2's load_model searches the whole asset folder (glob '**/name.bam', '.ursinamesh', '.obj', then
'.glb') on every call, even for a model it has loaded before or one that is not there at all ('quad').
A tower scene makes about 1500 such calls, so building it froze the window for many seconds.
install() remembers where each name was found (or that it was not found) and keeps every loaded model,
so a repeat load is a copy of the one in memory (Panda3D's loader would still check the file each time).

While a builder runs, on_load (if set) is called after every model load; the loading screen uses it
to redraw its bar.
"""
from panda3d.core import NodePath
from ursina import application

GEOMETRY = ('.bam', '.glb', '.gltf')     # loaded straight through Panda3D's loader (and its model pool)
on_load = None
_where = {}
_models = {}
_installed = False


def _resolve(name, path, file_types):
    """What Ursina's load_model would find: (filetype, filename) or None."""
    if '.' in name:
        file_types = ('.' + name.split('.', 1)[1],)
        name = name.split('.')[0]
    for filetype in file_types:
        for filename in path.glob('**/{}{}'.format(name, filetype)):
            return filetype, filename
    return None


def install():
    global _installed
    if _installed:
        return
    _installed = True
    import ursina
    from ursina import entity, mesh_importer
    original = mesh_importer.load_model

    def load_model(name, path=application.asset_folder, file_types=('.bam', '.ursinamesh', '.obj', '.glb', '.gltf',
                                                                       '.blend'), use_deepcopy=False):
        if not isinstance(name, str) or name.split('.')[0] in mesh_importer.imported_meshes:
            return original(name, path, file_types, use_deepcopy)        # Ursina's own cache: already fast
        key = (name, str(path), tuple(file_types))
        if key not in _where:
            _where[key] = _resolve(name, path, file_types)
        found = _where[key]
        if found is None:
            return None
        filetype, filename = found
        model = None
        if filetype in GEOMETRY:
            if filename not in _models:
                try:
                    _models[filename] = loader.loadModel(filename)       # noqa: F821  (Panda3D builtin)
                except Exception:
                    _models[filename] = None
            if _models[filename] is not None:
                model = NodePath(_models[filename].node().copySubgraph())
        if model is None:
            model = original(name, path, file_types, use_deepcopy)
        if on_load is not None:
            on_load()
        return model

    mesh_importer.load_model = entity.load_model = ursina.load_model = load_model
