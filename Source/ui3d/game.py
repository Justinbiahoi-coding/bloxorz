"""Tower mode in 3D: floors stacked in one building; win a floor, the block drops down the stairwell and
the camera follows it to the floor below. Arrows roll, Space swaps split cubes, R restarts the floor,
Esc quits."""
import math

from ursina import Entity, Text, Vec3, application, camera, color, held_keys, time, window

from engine import Tower
from engine.problem import DIRS
from ui.hud import floor_name

from .block import Block
from .floor import Floor
from .intro import Intro
from .world import FLOOR_H, aim_sun, point_camera

KEYS = {'left arrow': 'LEFT', 'right arrow': 'RIGHT', 'up arrow': 'DOWN', 'down arrow': 'UP'}
ROLL_S, FALL_S, DESCEND_S = 0.17, 0.45, 1.4
SKY = [(22, 28, 58), (20, 25, 52), (18, 22, 46), (16, 20, 40), (14, 17, 34)]   # night, roof .. lobby


def _ease(t):
    return t * t * (3 - 2 * t)


def _mix(a, b, k):
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


class TowerGame(Entity):
    def __init__(self, sun):
        super().__init__()
        self.sun = sun
        self.tower = Tower()
        self.floor = Floor(self.tower.session, 0, self.tower.count)
        self.next_floor = None
        self.block = Block()
        self.phase, self.t = 'play', 0.0
        camera.fov = 38
        self._place_block()
        self._aim(self.floor)
        self.hud_name = Text('', position=window.top_left + Vec3(0.06, -0.05, 0), scale=2.2, color=color.white)
        self.hud_info = Text('', position=window.top_left + Vec3(0.065, -0.12, 0), scale=1.2,
                             color=color.rgb(255, 200, 87))
        self.banner = Text('', origin=(0, 0), scale=2.4, color=color.white, y=0.05)
        self.panel = Entity(parent=camera.ui, model='quad', color=color.rgba(20, 26, 44, 190), z=1,
                            scale=(0.5, 0.17), position=window.top_left + Vec3(0.27, -0.095, 0))
        self._hud()
        self.intro = Intro(self.floor, self.tower.count, *self._camera_for(self.floor))
        self.phase = 'intro'
        self._show_hud(False)

    # ---- helpers ----
    def _place_block(self):
        self.block.place(self.tower.session, self.tower.session.state, self.floor.base)

    def _camera_for(self, floor):
        dist = floor.size * 0.95 + 4
        return floor.centre + Vec3(0, dist * 0.95, -dist * 0.78), floor.centre

    def _aim(self, floor):
        pos, target = self._camera_for(floor)
        camera.position = pos
        point_camera(camera, target)
        aim_sun(self.sun, target)
        k = floor.index / max(1, floor.count - 1)
        i = min(len(SKY) - 2, int(k * (len(SKY) - 1)))
        window.color = color.rgb(*_mix(SKY[i], SKY[i + 1], k * (len(SKY) - 1) - i))

    def _show_hud(self, on):
        for e in (self.hud_name, self.hud_info, self.panel):
            e.enabled = on

    def _hud(self):
        s = self.tower.session
        self.hud_name.text = floor_name(self.tower.index, self.tower.count)
        self.hud_info.text = 'LEVEL {} / {}     MOVES {}'.format(self.tower.index + 1, self.tower.count, s.moves)

    # ---- input ----
    def input(self, key):
        if key == 'escape':
            application.quit()
        if key == 'f':
            window.fullscreen = not window.fullscreen
        if self.phase == 'intro':
            if not key.endswith(' up'):
                self.intro.skip_or_enter()
            return
        if self.phase != 'play':
            return
        s = self.tower.session
        before = s.state
        if key in KEYS or key == 'space':
            action = KEYS.get(key, 'SWITCH')
            if not s.move(action):
                return
            if before.bridges != s.state.bridges:
                self.floor.refresh()
            if action != 'SWITCH' and self.block.start_roll(s, before, s.state, action, DIRS[action], self.floor.base):
                self.phase, self.t = 'roll', 0.0
            else:
                self._place_block()
                self._after_move()
        elif key == 'r':
            s.reset()
            self.floor.refresh()
            self._place_block()
        self._hud()

    def _after_move(self):
        if self.tower.session.won:
            self.phase, self.t = 'fall', 0.0

    # ---- per frame ----
    def update(self):
        dt = time.dt
        if self.floor.beacon:
            self.floor.beacon.color = color.rgb(255, 60, 50) if int(time.time() * 1.6) % 2 else color.rgb(90, 30, 30)
        if self.phase == 'intro':
            self.intro.step(dt)
            if self.intro.done:
                self.intro.destroy()
                self._aim(self.floor)
                self._show_hud(True)
                self.phase = 'play'
        elif self.phase == 'roll':
            self.t += dt / ROLL_S
            self.block.set_progress(min(1.0, self.t))
            if self.t >= 1:
                self.block.finish()
                self.phase = 'play'
                self._after_move()
                self._hud()
        elif self.phase == 'fall':                                  # down the stairwell
            self.t += dt / FALL_S
            for e in self.block.pieces:
                e.y -= dt * 3.2
                e.scale *= 0.985
            if self.t >= 1:
                self.block.clear()
                if self.tower.is_last:
                    self.phase = 'done'
                    self.banner.text = 'Ground floor!\n{} floors, {} moves'.format(
                        self.tower.count, self.tower.total_moves + self.tower.session.moves)
                else:
                    self.tower.descend()
                    self.next_floor = Floor(self.tower.session, self.tower.index, self.tower.count)
                    self.cam_from = (camera.position, self._camera_for(self.floor)[1])
                    self.phase, self.t = 'descend', 0.0
        elif self.phase == 'descend':                               # the camera follows to the floor below
            self.t += dt / DESCEND_S
            k = _ease(min(1.0, self.t))
            pos, target = self._camera_for(self.next_floor)
            start_pos, start_target = self.cam_from
            camera.position = start_pos + (pos - start_pos) * k
            point_camera(camera, start_target + (target - start_target) * k)
            if self.t >= 1:
                self.floor.destroy()
                self.floor, self.next_floor = self.next_floor, None
                self._aim(self.floor)
                self._place_block()
                self.phase = 'play'
                self._hud()
