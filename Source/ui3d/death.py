"""The dead come for the bin: what happens when the block rolls off the path.

Shared by the Tower and Free Play so losing looks the same in both: the block tips over the edge,
the zombies on the floor run to it and close in, the lid bursts off, the picture goes black and the cat
lies still while GAME OVER drops in. The scene using it provides .session, .floor, .block, .prowl,
.sun, .hud, ._show_hud(on), and .phase / .t; it calls _death_update(dt) while phase is in DEATH_PHASES.
"""
import math

from ursina import Entity, Text, Vec3, camera, color, destroy, window

from engine.problem import DIRS

from .cat import Cat, available as cat_available
from .floor import glow
from .world import aim_sun, move_lantern, point_camera

DEATH_PHASES = ('fall', 'swarm', 'bite', 'over')


class DeathScene:
    def _init_death(self, over_hint):
        """Build the game-over pieces now, so the first death does not hitch."""
        self.cut = self.cut_cat = None
        self._over_alpha = [-1, -1]
        self.flash = Entity(parent=camera.ui, model='quad', scale=(4, 2), z=2, color=color.rgba(0, 0, 0, 0), enabled=False)
        self.over_text = Text('GAME OVER', origin=(0, 0), scale=4.4, y=0.08, z=-3, color=color.rgba(255, 240, 230, 0), enabled=False)
        self.over_sub = Text(over_hint, origin=(0, 0), scale=1.6, y=-0.32, z=-3, color=color.rgba(235, 230, 220, 0), enabled=False)
        self.dead_cat = Cat(scale=2.4) if cat_available() else None
        if self.dead_cat:
            self.dead_cat.root.enabled = False
        for name in ('bin_block_body', 'bin_block_lid'):
            Entity(model='models/bin/' + name, enabled=False)

    def _clear_death(self):
        """Back to the board after a death (retry): remove the cut-scene pieces and the black room."""
        if self.cut:
            destroy(self.cut)
        if self.cut_cat:
            self.cut_cat.root.enabled = False
        if getattr(self, 'cut_shadow', None):
            destroy(self.cut_shadow)
            self.cut_shadow = None
        self.cut = self.cut_cat = None
        self.flash.enabled = self.over_text.enabled = self.over_sub.enabled = False
        self._over_alpha = [-1, -1]
        camera.fov = 42

    def _close_death(self):
        for name in ('cut', 'cut_shadow', 'flash', 'over_text', 'over_sub'):
            obj = getattr(self, name, None)
            if obj is not None:
                destroy(obj)
        if getattr(self, 'dead_cat', None) is not None:
            self.dead_cat.destroy()

    def _death_update(self, dt):
        if self.phase == 'fall':
            self.t += dt / self.block.duration
            self.block.set_progress(min(1.0, self.t))
            if self.t >= 1:
                self.block.finish()
                self._begin_swarm()
        elif self.phase == 'swarm':
            self.t += dt
            self.prowl.face(self.swarm_centre)
            cam_pos = self.swarm_centre + Vec3(0, 9.0, -10.5)
            k = min(1.0, dt * 2.5)
            camera.position = camera.position + (cam_pos - camera.position) * k
            point_camera(camera, self.swarm_centre + Vec3(0, 0.6, 0))
            if self.prowl.arrived or self.t > 6.0:
                self._begin_bite()
        elif self.phase == 'bite':
            self.t += dt
            self._bite(dt)
        elif self.phase == 'over':
            self.t += dt
            self._over()

    def _fall(self, action):
        if action not in DIRS:                   # only a roll can go over the edge
            return
        s = self.session
        if self.block.start_fall(s, s.state, action, DIRS[action], self.floor.base):
            self.phase, self.t = 'fall', 0.0
        else:
            self._begin_swarm()

    def _bin_spot(self):
        pc = self.block.pieces[0].position
        return Vec3(pc.x, self.floor.base, pc.z)

    def _begin_swarm(self):
        self.swarm_centre = self._bin_spot()
        self.prowl.converge(self.swarm_centre)
        self.phase, self.t = 'swarm', 0.0

    VOID = Vec3(0, -800, 0)                                  # a black room far away for the game-over picture

    def _begin_bite(self):
        """The bin is surrounded. Swap the player piece for a bin with a loose lid; the cat stays hidden inside."""
        import builtins
        piece = self.block.pieces[0]
        self.cut = Entity(position=piece.position)
        self.cut.setQuat(builtins.render, piece.spinner.getQuat(builtins.render))
        self.cut_body = Entity(parent=self.cut, model='models/bin/bin_block_body')
        self.cut_lid = Entity(parent=self.cut, model='models/bin/bin_block_lid')
        for e in (self.cut_body, self.cut_lid):
            for m in e.findAllMaterials():
                m.setMetallic(0)
        piece.enabled = False
        self.cut_cat = self.dead_cat
        if self.cut_cat:
            self.cut_cat.root.enabled = False
        self.cut_pos = Vec3(self.cut.position)
        self.void_on = False
        self.phase, self.t = 'bite', 0.0

    def _bite(self, dt):
        """0-0.5 they close in and the bin shakes; 0.5-1.3 the lid bursts off; 1.6-2.2 the picture goes black;
        then the cat lies still in the dark (see _over)."""
        t = self.t
        self.prowl.face(self.swarm_centre)
        self.prowl.lunge(min(1.0, t / 0.5))
        shake = math.sin(t * 60) * 0.05 * (1.0 if t < 1.4 else 0.0)
        self.cut.position = self.cut_pos + Vec3(shake, 0, -shake * 0.6)
        if t > 0.5:
            u = min(1.0, (t - 0.5) / 0.8)
            self.cut_lid.world_position = self.cut_pos + Vec3(1.8 * u, 3.4 * math.sin(math.pi * u) + 0.6 * u, -1.2 * u)
            self.cut_lid.rotation = (0, 0, 540 * u)
        cam_target = self.cut_pos + Vec3(0, 0.9, 0)
        cam_pos = self.cut_pos + Vec3(1.2, 4.2 - 0.6 * min(1.0, t / 1.5), -6.2 + 1.0 * min(1.0, t / 1.5))
        camera.position = camera.position + (cam_pos - camera.position) * min(1.0, dt * 3)
        point_camera(camera, cam_target)
        if t > 1.6:
            self.flash.enabled = True
            self.flash.color = color.rgba(0, 0, 0, int(255 * min(1.0, (t - 1.6) / 0.5)))
        if t > 2.2:                                          # black: move to the dark room, cat lying still in the middle
            self.void_on = True
            self._show_hud(False)
            window.color = color.black
            if self.cut_cat:
                c = self.cut_cat.root
                c.enabled = True
                c.position = self.VOID + Vec3(0.2, 0.3, 0)
                c.rotation = (0, 90, 90)                    # flat on its side, legs stretched out, seen in profile
                self.cut_cat.show('Run_F', 4)
                self.cut_shadow = glow(self.cut_cat.root.parent or self.cut_cat.root, self.VOID + Vec3(0.2, 0.02, 0.1), (3.6, 0.02, 1.3),
                                       color.rgba(60, 60, 66, 120), model='circle', rotation_x=90)
            camera.position = self.VOID + Vec3(0, 3.2, -7.0)
            point_camera(camera, self.VOID + Vec3(0, 0.3, 0))
            camera.fov = 32
            aim_sun(self.sun, self.VOID + Vec3(0, 0.4, 0))
            move_lantern(self.sun, self.VOID + Vec3(0, 0.2, 0.4))
            self.phase, self.t = 'over', 0.0

    @staticmethod
    def _bounce(k):
        """Ease-out bounce: drops, hits the ground, bounces twice."""
        k = max(0.0, min(1.0, k))
        if k < 1 / 2.75:
            return 7.5625 * k * k
        if k < 2 / 2.75:
            k -= 1.5 / 2.75
            return 7.5625 * k * k + 0.75
        if k < 2.5 / 2.75:
            k -= 2.25 / 2.75
            return 7.5625 * k * k + 0.9375
        k -= 2.625 / 2.75
        return 7.5625 * k * k + 0.984375

    def _over(self):
        """Out of the black, the cat lies there; GAME OVER drops in from the top of the screen."""
        t = self.t
        self.flash.color = color.rgba(0, 0, 0, int(255 * max(0.0, 1 - t / 0.5)))
        self.over_text.enabled = self.over_sub.enabled = True
        k = self._bounce((t - 0.5) / 1.0)
        self.over_text.y = 0.62 + (0.2 - 0.62) * k
        a = 255 if t > 0.5 else 0                                  # rebuilding a Text's colour is slow: only when it changes
        if a != self._over_alpha[0]:
            self._over_alpha[0] = a
            self.over_text.color = color.rgba(255, 240, 230, a)
        b = int(23 * round(10 * max(0.0, min(1.0, (t - 1.8) / 0.5))))
        if b != self._over_alpha[1]:
            self._over_alpha[1] = b
            self.over_sub.color = color.rgba(235, 230, 220, b)
