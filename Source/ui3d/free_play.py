"""Single-level Free Play for the 3D front-end.

Play is Youmei's: arrows roll, Space switches cubes, R restarts, a move pressed mid-roll is queued,
falling off tips the block over the edge, and the result offers the next level of the same set.
The level is dressed as a storey of the tower (ui3d/floor.py): ruined room, furniture, the dead on their
beat, and the goal is the elevator, whose doors close when the block is in.
The UI around it is the shared HUD (ui3d/hud.py) with Pause, Hint and Solve.
"""
from ursina import Entity, Vec3, camera, color, destroy, time, window

from engine import GameSession, solve
from engine.catalog import TUTORIAL_NAMES, TUTORIAL_TIPS, next_level
from engine.problem import DIRS
from . import settings
from . import widgets as w
from .block import Block
from .controls import PlayControls
from .floor import Floor
from .prowl import Prowlers
from .hud import GameHUD
from .screens.dialogs import PauseMenu, ResultDialog
from .world import aim_sun, move_lantern, point_camera

KEYS = {'left arrow': 'LEFT', 'right arrow': 'RIGHT', 'up arrow': 'DOWN', 'down arrow': 'UP'}
SKY = (14, 17, 34)


class FreePlayGame(PlayControls, Entity):
    """app: on_menu(), on_next(level), on_levels(), on_settings(on_close)."""

    def __init__(self, sun, level_number, mode, on_menu, on_next, on_levels=None, on_settings=None):
        super().__init__()
        self.sun = sun
        self.level_number = level_number
        self.mode = mode
        self.on_menu, self.on_next = on_menu, on_next
        self.on_levels, self.on_settings = on_levels, on_settings
        self.session = GameSession(level_number)
        self.floor = Floor(self.session, 0, 1, free_play=True)
        self.prowl = Prowlers(self.floor, count=4, seed=level_number)    # only walking their beat here
        self.block = Block()
        self.phase, self.t = 'play', 0.0
        self.queued = None
        self.fall_pieces = []
        self.dialog = None
        camera.fov = 42
        self._place_block()
        self._aim()
        self.hud = GameHUD({'new_game': self.new_game, 'restart': self.restart, 'hint': self.hint,
                            'solve': self.solve, 'pause': self.pause})
        self.hud.set_tip(TUTORIAL_TIPS.get(level_number))
        self.hud.set_legend({self.session.tile_at(x, y) for x, y in self.session.level.kinds})
        self._hud()

    # ---- view ----
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
        name = TUTORIAL_NAMES.get(self.level_number, 'Level {}'.format(self.level_number))
        stats = [('Moves', '{:02d}'.format(self.session.moves), '')]
        if self.session.is_split:
            stats.append(('Cube', 'AB'[self.session.active], ''))
        self.hud.set(name, stats)

    # ---- input ----
    def input(self, key):
        if w.Modal.busy():
            return
        if key == 'f':
            settings.set('fullscreen', not window.fullscreen)
            window.fullscreen = settings.get('fullscreen')
            return
        if key == 'escape':
            self.pause()
            return
        if self.phase == 'roll' and (key in KEYS or key == 'space'):
            self.queued = key
            return
        if self.phase != 'play':
            return
        if key == 'r':
            self.restart()
            return
        if key == 'h':
            self.hint()
            return
        if key not in KEYS and key != 'space':
            return
        self.clear_hint()
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

    # ---- toolbar actions ----
    def restart(self):
        self.stop_auto()
        self.clear_hint()
        self.assisted = False
        self.session.reset()
        self.floor.refresh()
        self._place_block()
        self._aim()
        self.phase, self.t = 'play', 0.0
        self._hud()

    def new_game(self):
        """Back to level select; asks first if this level is under way."""
        if not self.on_levels:
            return
        if self.session.moves and self.phase in ('play', 'roll'):
            w.ConfirmDialog('Leave this level?', 'Your {} moves here will be lost.'.format(self.session.moves),
                            self.on_levels, confirm='Leave', danger=True)
        else:
            self.on_levels()

    def pause(self):
        if self.phase not in ('play', 'roll') or w.Modal.any_open():
            return
        self.stop_auto()
        PauseMenu(resume=None, restart=self.restart, new_game=self.new_game,
                  settings=(lambda: self.on_settings(self.pause)) if self.on_settings else None,
                  main_menu=self._leave)

    def _leave(self):
        if self.session.moves and self.phase in ('play', 'roll'):
            w.ConfirmDialog('Return to main menu?', 'Your progress on this level will be lost.', self.on_menu,
                            confirm='Leave', danger=True)
        else:
            self.on_menu()

    # ---- play ----
    def start_fall(self):
        self.clear_hint()
        self.fall_pieces = list(self.block.pieces)
        self.phase, self.t = 'fall', 0.0

    def _after_move(self):
        if self.session.won:
            self.phase, self.t = 'win', 0.0

    def _show_result(self, kind):
        self.phase = 'result'
        self.hud.show(False)
        won = kind == 'win'
        best = None
        if won:
            if not self.assisted:
                settings.mark_completed(self.level_number)
            result = solve(self.level_number, 'BFS', measure_memory=False)
            best = result.solution_length
        nxt = next_level(self.mode, self.level_number) if won else None
        self.dialog = ResultDialog(
            won, self.session.moves, best,
            on_next=(lambda: self.on_next(nxt)) if nxt is not None else None,
            on_retry=lambda: self.on_next(self.level_number),
            on_levels=self.on_levels, on_menu=self.on_menu)

    def update(self):
        dt = time.dt
        self.block.tick(dt, self.phase == 'play')
        self.floor.animate(time.time())
        self.prowl.update(dt)
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
        elif self.phase == 'win':                     # in the elevator: the doors close, as in the tower
            self.t += dt
            if self.floor.lift:
                k = min(1.0, self.t / .6)
                self.floor.lift.set_open(1 - k * k * (3 - 2 * k))
            if self.t >= .8:
                self._show_result('win')

    def close(self):
        self.stop_auto()
        self.clear_hint()
        if self.dialog:
            self.dialog.close()
        for m in list(w.Modal.stack):
            m.close()
        self.block.clear()
        self.prowl.destroy()
        self.floor.destroy()
        destroy(self.hud)
        destroy(self)
