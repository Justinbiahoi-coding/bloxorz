"""Hint and Solve for any play scene (Free Play, the Tower).

The scene provides .session, .floor, .phase ('play' when it takes a move), .hud (GameHUD) and .input(key).
"""
from ursina import destroy

from . import theme
from . import widgets as w
from .autoplay import Autoplayer, ghost, solve_from
from .hud import SHORT


class PlayControls:
    hint_ghost = None
    auto = None
    solve_notice = None
    assisted = False        # a solver played moves here: Free Play does not count the level as completed

    def hint(self):
        if self.phase != 'play':
            return
        self.clear_hint()
        nxt = self.session.request_hint()
        if nxt is None:
            w.Toast('No way forward from here: restart with R', col=theme.ORANGE)
            return
        self.hint_ghost = ghost(self.floor, self.session, nxt.state)

    def clear_hint(self):
        if self.hint_ghost is not None:
            destroy(self.hint_ghost)
            self.hint_ghost = None

    def solve(self, algorithm):
        """Solve from the current state and play the moves; any player key takes over."""
        if self.phase != 'play':
            return
        self.stop_auto()
        self.clear_hint()
        if self.solve_notice:
            self.solve_notice._gone()
        self.solve_notice = None
        moves, result, error = solve_from(self.session, algorithm)
        if error:
            self.solve_notice = w.Toast(error, col=theme.ORANGE, top=.35)
            return
        name = SHORT[algorithm]
        self.assisted = True
        self.solve_notice = w.Toast('{}: {} moves · cost {} · {} nodes expanded · {:.1f} ms'.format(
            name, result.solution_length, result.solution_cost, result.expanded, result.elapsed_ms), top=.35)
        self.hud.set_status('{} · solving'.format(name))
        self.auto = Autoplayer(self, moves, on_step=lambda d, n: self.hud.set_status(
            '{} · action {} / {}   ·   any key takes over'.format(name, d, n)), on_end=self._auto_end)

    def _auto_end(self, finished):
        self.auto = None
        if self.hud:
            self.hud.set_status(None)

    def stop_auto(self):
        if self.auto is not None:
            self.auto.stop()
