"""Single-level Free Play for the 3D front-end."""
from ursina import Button, Entity, Text, Vec3, camera, color, destroy, time, window

from engine import GameSession
from engine.catalog import TUTORIAL_NAMES, TUTORIAL_TIPS, next_level
from engine.problem import DIRS
from .block import Block
from .floor import Floor
from .world import aim_sun, move_lantern, point_camera

KEYS = {'left arrow': 'LEFT', 'right arrow': 'RIGHT', 'up arrow': 'DOWN', 'down arrow': 'UP'}
SKY = (14, 17, 34)


class FreePlayGame(Entity):
    def __init__(self, sun, level_number, mode, on_menu, on_next):
        super().__init__()
        self.sun = sun
        self.level_number = level_number
        self.mode = mode
        self.on_menu = on_menu
        self.on_next = on_next
        self.session = GameSession(level_number)
        self.floor = Floor(self.session, 0, 1, free_play=True)
        self.block = Block()
        self.phase, self.t = 'play', 0.0
        self.queued = None
        self.fall_pieces = []
        self.result_root = None
        camera.fov = 42
        self._place_block()
        self._aim()
        self.hud_name = Text('', position=window.top_left + Vec3(0.06, -0.05, 0), scale=2.2, color=color.white)
        self.hud_info = Text('', position=window.top_left + Vec3(0.065, -0.12, 0), scale=1.2,
                             color=color.rgb(255, 200, 87))
        tip = TUTORIAL_TIPS.get(level_number)
        self.tip = Text(tip or 'Arrows move  |  Space switches cubes  |  R restarts  |  Esc menu',
                        origin=(0, 0), y=.40, scale=1.05, wordwrap=70,
                        color=color.rgb(250, 244, 232), background=True)
        self._hud()

    def _place_block(self):
        self.block.place(self.session, self.session.state, self.floor.base)

    def _player_pos(self):
        pieces = self.block.pieces
        if not pieces:
            return self.floor.centre
        p = sum((e.position for e in pieces), Vec3(0)) / len(pieces)
        return Vec3(p.x, self.floor.base, p.z)

    def _camera_for(self):
        focus = self._player_pos()
        c = self.floor.centre
        target = Vec3(c.x * 0.8 + focus.x * 0.2, self.floor.base + 0.4, c.z * 0.8 + focus.z * 0.2)
        dist = max(20.0, min(40.0, self.floor.span * 1.35 + 12.0))
        return target + Vec3(0, dist * 0.87, -dist * 0.5), target

    def _aim(self):
        pos, target = self._camera_for()
        camera.position = pos
        point_camera(camera, target)
        aim_sun(self.sun, target)
        window.color = color.rgb(*SKY)

    def _hud(self):
        label = TUTORIAL_NAMES.get(self.level_number, 'LEVEL {}'.format(self.level_number))
        self.hud_name.text = label
        self.hud_info.text = 'MOVES {}'.format(self.session.moves)

    def input(self, key):
        if key == 'f':
            window.fullscreen = not window.fullscreen
            return
        if key == 'escape':
            if self.phase == 'result':
                self.on_menu()
            else:
                self.on_menu()
            return
        if self.phase == 'result':
            if key in ('r', 'enter') and self._result_kind == 'lose':
                self.on_next(self.level_number)
            elif key == 'n' and self._result_kind == 'win':
                nxt = next_level(self.mode, self.level_number)
                if nxt is not None:
                    self.on_next(nxt)
            elif key == 'r' and self._result_kind == 'win':
                self.on_next(self.level_number)
            return
        if self.phase == 'roll' and (key in KEYS or key == 'space'):
            self.queued = key
            return
        if self.phase != 'play':
            return
        if key == 'r':
            self.restart()
            return
        if key not in KEYS and key != 'space':
            return
        action = KEYS.get(key, 'SWITCH')
        before = self.session.state
        status, _, after = self.session.attempt_move(action)
        if status == 'fell':
            self.start_fall()
            return
        if before.bridges != self.session.state.bridges:
            self.floor.refresh()
        if action != 'SWITCH' and after is not None and self.block.start_roll(
                self.session, before, after, action, DIRS[action], self.floor.base):
            self.phase, self.t = 'roll', 0.0
        else:
            self._place_block()
            self._after_move()
        self._hud()

    def restart(self):
        self.session.reset()
        self.floor.refresh()
        self._place_block()
        self._aim()
        self.phase, self.t = 'play', 0.0
        self._hud()

    def start_fall(self):
        self.fall_pieces = list(self.block.pieces)
        self.phase, self.t = 'fall', 0.0

    def _after_move(self):
        if self.session.won:
            self.phase, self.t = 'win', 0.0

    def _show_result(self, kind):
        self.phase = 'result'
        self._result_kind = kind
        self.hud_name.enabled = self.hud_info.enabled = self.tip.enabled = False
        self.result_root = Entity(parent=camera.ui)
        shade = Entity(parent=self.result_root, model='quad', scale=(4, 2), color=color.rgba(8, 12, 28, 210), z=1)
        title = 'LEVEL CLEARED' if kind == 'win' else 'YOU FELL'
        title_color = color.rgb(255, 200, 87) if kind == 'win' else color.rgb(255, 138, 91)
        Text(title, parent=self.result_root, origin=(0, 0), y=.22, scale=5, color=title_color)
        Text('Level {}  -  {} moves'.format(self.level_number, self.session.moves),
             parent=self.result_root, origin=(0, 0), y=.12, scale=1.5, color=color.white)
        options = []
        if kind == 'win' and next_level(self.mode, self.level_number) is not None:
            options.append(('Next Level', lambda: self.on_next(next_level(self.mode, self.level_number))))
        options.append(('Retry', lambda: self.on_next(self.level_number)))
        options.append(('Main Menu', self.on_menu))
        for i, (label, callback) in enumerate(options):
            Button(label, parent=self.result_root, scale=(.42, .075), y=.01 - i * .11,
                   color=color.rgb(44, 58, 94), on_click=callback)

    def update(self):
        dt = time.dt
        self.block.tick(dt, self.phase == 'play')
        self.floor.animate(time.time())
        if self.phase in ('play', 'roll'):
            pos, target = self._camera_for()
            k = min(1.0, dt * 3.0)
            camera.position = camera.position + (pos - camera.position) * k
            prev = getattr(self, 'cam_target', target)
            self.cam_target = prev + (target - prev) * k
            point_camera(camera, self.cam_target)
            move_lantern(self.sun, self._player_pos())
            aim_sun(self.sun, self.cam_target)
        if self.phase == 'roll':
            self.t += dt / self.block.duration
            self.block.set_progress(min(1.0, self.t))
            if self.t >= 1:
                self.block.finish()
                self.phase = 'play'
                self._after_move()
                self._hud()
                if self.queued and self.phase == 'play':
                    key, self.queued = self.queued, None
                    self.input(key)
        elif self.phase == 'fall':
            self.t += dt
            for piece in self.fall_pieces:
                piece.y -= dt * 2.8
                piece.rotation_x += dt * 220
            if self.t >= .7:
                self._show_result('lose')
        elif self.phase == 'win':
            self.t += dt
            if self.t >= .8:
                self._show_result('win')
    def close(self):
        self.block.clear()
        self.floor.destroy()
        for e in (self.hud_name, self.hud_info, self.tip, self.result_root):
            if e is not None:
                destroy(e)
        destroy(self)
