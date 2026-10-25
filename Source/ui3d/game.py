"""Tower mode in 3D: the climb starts in the lobby and ends on the roof. Win a floor by standing in its
elevator: the doors close, the car rides up with the camera, and the next floor opens around its arrival
elevator. Arrows roll, Space swaps split cubes, R restarts the floor,
Esc quits."""
import math

from ursina import Entity, Text, Vec3, application, camera, color, held_keys, time, window

from engine import Tower
from engine.problem import DIRS

from .block import Block
from .floor import Floor
from .intro import Intro
from .world import FLOOR_H, aim_sun, move_lantern, point_camera

KEYS = {'left arrow': 'LEFT', 'right arrow': 'RIGHT', 'up arrow': 'DOWN', 'down arrow': 'UP'}
ROLL_S, DOORS_S, RIDE_S = 0.17, 0.6, 1.6
SKY = [(14, 17, 34), (16, 20, 40), (18, 22, 46), (20, 25, 52), (22, 28, 58)]   # night, lobby .. roof


def floor_name(index, count):
    """Bottom-up: LOBBY, FLOOR 1 .. FLOOR n, ROOFTOP."""
    if index == 0:
        return 'LOBBY'
    if index == count - 1:
        return 'ROOFTOP'
    return 'FLOOR {}'.format(index)


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
        self.queued = None
        camera.fov = 42
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
        self.intro.light(self.sun)
        self.phase = 'intro'
        self._show_hud(False)
        self._show_floor(False)                              # the lobby sits inside the intro's tower

    def _show_floor(self, on):
        self.floor.root.enabled = on
        for e in self.block.pieces:
            e.enabled = on
        for c in getattr(self.block, 'chars', []):
            c['shadow'].enabled = on

    # ---- helpers ----
    def _place_block(self):
        self.block.place(self.tower.session, self.tower.session.state, self.floor.base)

    def _player_pos(self, floor):
        pieces = self.block.pieces if floor is self.floor else []
        if not pieces:
            return floor.centre
        p = sum((e.position for e in pieces), Vec3(0)) / len(pieces)
        return Vec3(p.x, floor.base, p.z)

    def _camera_for(self, floor, focus=None):
        """A far, steep camera (about 60 degrees, like Rolling Cat) that keeps the whole floor in view and
        only leans a little towards the player."""
        focus = focus if focus is not None else self._player_pos(floor)
        c = floor.centre
        target = Vec3(c.x * 0.8 + focus.x * 0.2, floor.base + 0.4, c.z * 0.8 + focus.z * 0.2)
        dist = max(20.0, min(40.0, floor.span * 1.35 + 12.0))
        return target + Vec3(0, dist * 0.87, -dist * 0.5), target

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
        if self.phase == 'roll' and (key in KEYS or key == 'space'):
            self.queued = key                                    # buffer one move so play feels responsive
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
            self.phase, self.t = 'close', 0.0

    # ---- per frame ----
    def update(self):
        dt = time.dt
        self.block.tick(dt, self.phase == 'play')
        self.floor.animate(time.time())
        if self.phase in ('play', 'roll'):                    # camera and lantern follow the player smoothly
            pos, target = self._camera_for(self.floor)
            k = min(1.0, dt * 3.0)
            camera.position = camera.position + (pos - camera.position) * k
            prev = getattr(self, 'cam_target', target)
            self.cam_target = prev + (target - prev) * k
            point_camera(camera, self.cam_target)
            move_lantern(self.sun, self._player_pos(self.floor))
            aim_sun(self.sun, self.cam_target)
        if self.floor.beacon:
            self.floor.beacon.color = color.rgb(255, 60, 50) if int(time.time() * 1.6) % 2 else color.rgb(90, 30, 30)
        if self.phase == 'intro':
            self.intro.step(dt)
            if self.intro.done:
                self.intro.destroy()
                self._show_floor(True)
                self._aim(self.floor)
                self._show_hud(True)
                self.phase = 'play'
        elif self.phase == 'roll':
            self.t += dt / self.block.duration
            self.block.set_progress(min(1.0, self.t))
            if self.t >= 1:
                self.block.finish()
                self.phase = 'play'
                self._after_move()
                self._hud()
                if self.queued and self.phase == 'play':     # a key pressed mid-move plays right after
                    key, self.queued = self.queued, None
                    self.input(key)
        elif self.phase == 'close':                                 # standing in the elevator: doors close
            self.t += dt / DOORS_S
            if self.floor.lift:
                self.floor.lift.set_open(1 - _ease(min(1.0, self.t)))
            if self.t >= 1:
                if self.tower.is_last:
                    self.phase = 'done'
                    self.banner.text = 'You made it to the roof!\n{} floors, {} moves'.format(
                        self.tower.count, self.tower.total_moves + self.tower.session.moves)
                    return
                for c in getattr(self.block, 'chars', []):
                    c['shadow'].enabled = False
                self.ride = [(e, e.y) for e in self.block.pieces] + [(self.floor.lift.root, self.floor.lift.root.y)]
                self.tower.descend()                                # (Tower.descend = next level)
                self.next_floor = Floor(self.tower.session, self.tower.index, self.tower.count)
                self.cam_from = (camera.position, self._camera_for(self.floor)[1])
                self.phase, self.t = 'ride', 0.0
        elif self.phase == 'ride':                                  # the car and the camera go up a storey
            self.t += dt / RIDE_S
            k = _ease(min(1.0, self.t))
            rise = (self.next_floor.base - self.floor.base) * k
            for e, y0 in self.ride:
                e.y = y0 + rise
            pos, target = self._camera_for(self.next_floor)
            start_pos, start_target = self.cam_from
            camera.position = start_pos + (pos - start_pos) * k
            point_camera(camera, start_target + (target - start_target) * k)
            if self.t >= 1:
                self.floor.destroy()
                self.floor, self.next_floor = self.next_floor, None
                self._aim(self.floor)
                self._place_block()
                self.phase, self.t = 'open', 0.0
                self._hud()
        elif self.phase == 'open':                                  # arrival doors slide open
            self.t += dt / DOORS_S
            if self.floor.arrival:
                self.floor.arrival.set_open(_ease(min(1.0, self.t)))
            if self.t >= 1:
                self.phase = 'play'
