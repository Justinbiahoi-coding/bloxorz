"""The ruined street and the tower from the opening, as a slowly drifting backdrop behind the menus.

Same set, models and light as the intro (street.py, tower.glb, Intro.light), without the cast:
the camera hangs back down the avenue and sways, so the tower stands on the right half of the
screen while the menu sits on the left.
"""
import math

from ursina import Entity, Vec3, camera, color, destroy, time, window

from engine import FLOORS, Level
from .floor import MX, MY, prop
from .street import Street
from .world import ASSETS, point_camera, set_exposure

SKY = (150, 124, 104)           # smoke-browned daylight, as in the intro


def lobby_footprint():
    """The lobby floor's (x0, y0, x1, y1), as Floor computes it: the tower model is built around it."""
    kinds = Level(FLOORS[0]).kinds
    xs, ys = [x for x, _ in kinds], [y for _, y in kinds]
    return min(xs) - MX, min(ys) - MY, max(xs) + MX, max(ys) + MY


class CityBackdrop(Entity):
    """Build with build_steps() one step per frame (so a loading bar can move), then it animates itself."""

    def __init__(self, sun):
        super().__init__()
        self.sun = sun
        fx0, fy0, fx1, fy1 = lobby_footprint()
        self.cx, self.cz = (fx0 + fx1) / 2, -(fy0 + fy1) / 2
        self.d = fy1 - fy0 + 2.2
        self.door_z = self.cz - self.d / 2 - 1.2
        self.root = Entity(parent=self)
        self.street = None
        self.t = 0.0
        self.ready = False

    def build_steps(self):
        """Yields (fraction done, caption) while it builds."""
        from panda3d.core import Fog
        yield .1, 'Clearing the street'
        fog = Fog('smoke')
        fog.setColor(0.60, 0.49, 0.41)
        fog.setExpDensity(0.0036)
        self.root.setFog(fog)
        self.street = Street(self.cx, self.cz - self.d / 2 - 1.0, length=76, width=13)
        self.street.root.reparent_to(self.root)
        yield .75, 'Raising the tower'
        if (ASSETS / 'models' / 'tower.glb').exists():
            prop(self.root, 'tower', Vec3(self.cx, 0, self.cz), 0, 1)
        self._light()
        self.ready = True
        self.update()
        yield 1.0, 'Ready'

    def _light(self):
        sun = self.sun
        sun.setPos(self.cx - 60, 70, self.cz + 20)
        sun.lookAt(self.cx, 0, self.street.z0 - 30)
        set_exposure(sun, 2.1, 1.9)
        c = sun.node().getColor()
        sun.node().setColor((c[0], c[1] * 0.78, c[2] * 0.58, c[3]))

    def update(self):
        if not self.ready:
            return
        self.t += time.dt
        t = self.t
        sway = math.sin(t * 0.09)
        camera.fov = 50
        camera.position = Vec3(self.cx - 1.5 + sway * 2.0, 5.5 + math.sin(t * 0.06) * 0.5, self.door_z - 72)
        point_camera(camera, Vec3(self.cx - 15 + sway, 22, self.cz))
        self.street.flicker(t)
        window.color = color.rgb(*SKY)

    def close(self):
        set_exposure(self.sun, 1.0, 1.0)
        if self.street:
            self.street.destroy()
        destroy(self)
