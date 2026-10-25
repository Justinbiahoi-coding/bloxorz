"""The cat (Zoomies by Scarlet Games): a flipbook of baked skinned poses, see tools/unity_cat.py.

The Mecanim clips were sampled on the CPU into one static model per pose (models/cat/Run_F_NN, Pet_sit_NN);
``Cat`` shows one at a time, so a run cycle or a sitting idle plays like a sprite sheet. The model's forward is
-z at yaw 0, the same as the old character: yaw 180 runs towards +z. ``pose(t, walking)`` matches Zombie's.
"""
from ursina import Entity, destroy

from .world import ASSETS

DIR = ASSETS / 'models' / 'cat'
RUN, SIT = 8, 6
SCALE = 2.4                       # the cat is about a quarter of a cell tall: make it a house cat next to people


def available():
    return (DIR / 'Run_F_00.glb').exists()


class Cat:
    def __init__(self, pos=(0, 0, 0), yaw=0.0, scale=SCALE, parent=None):
        self.root = Entity(parent=parent, position=pos, rotation_y=yaw)
        self.frames = {}
        for kind, n in (('Run_F', RUN), ('Pet_sit', SIT)):
            self.frames[kind] = []
            for i in range(n):
                e = Entity(parent=self.root, model='models/cat/%s_%02d' % (kind, i), scale=scale, enabled=False)
                for m in e.findAllMaterials():
                    m.setMetallic(0)
                e.setColorScale(1, 1, 1, 1)                      # the white skin blows out under the bright lights
                self.frames[kind].append(e)
        b = self.frames['Run_F'][0].model_bounds                       # stand it on its feet, centred on x/z
        self.offset = (-b.center.x * scale, -b.start.y * scale, -b.center.z * scale)
        for es in self.frames.values():
            for e in es:
                e.position = self.offset
        self.shown = None
        self.pose(0.0, False)

    def show(self, kind, i):
        if self.shown is not None:
            self.shown.enabled = False
        self.shown = self.frames[kind][i % len(self.frames[kind])]
        self.shown.enabled = True

    def pose(self, t, walking=False):
        """Run cycle while ``walking``, otherwise a slow sit-and-sway."""
        if walking:
            self.show('Run_F', int(t * 12))
        else:
            self.show('Pet_sit', int(t * 3))

    def destroy(self):
        destroy(self.root)
