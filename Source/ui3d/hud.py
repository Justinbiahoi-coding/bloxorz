"""In-game HUD shared by Free Play and the Tower, kept to the screen edges so the board stays clear.

  top left      HUDBar: level name, moves (and floor in the Tower), then the tutorial tip under it
  top right     toolbar: New Game, Restart, Hint, Solve (opens BFS / DFS / UCS / A*), Pause
  bottom right  legend of the tile kinds on this level (Settings > Tile legend)
  bottom        key hints, and a status pill while a solver plays the moves
"""
from ursina import Entity, camera, color, destroy, window

from engine import ALGORITHM_NAMES, Bloxorz, solve_problem
from . import icons, settings, theme
from . import widgets as w

SHORT = {'DFS': 'DFS', 'BFS': 'BFS', 'Uniform Cost Search': 'UCS', 'A*': 'A*'}
ORDER = ALGORITHM_NAMES
_ready = {}


def implemented(name):
    """Whether the engine has this solver yet (one cheap run on level 1, remembered)."""
    if name not in _ready:
        try:
            solve_problem(Bloxorz(1), name)
            _ready[name] = True
        except NotImplementedError:
            _ready[name] = False
    return _ready[name]

# (tile kind from GameSession.tile_at, label, chip colour) in the order the legend lists them
LEGEND = [
    ('floor', 'Floor', color.rgb(96, 100, 112)),
    ('goal', 'Goal', color.rgb(255, 205, 90)),
    ('fragile', 'Fragile', color.rgb(214, 104, 52)),
    ('soft', 'Soft switch', color.rgb(70, 130, 220)),
    ('heavy', 'Heavy switch', color.rgb(50, 50, 58)),
    ('split', 'Split', color.rgb(150, 80, 200)),
    ('bridge_open', 'Bridge (open)', color.rgb(180, 186, 196)),
    ('bridge_closed', 'Bridge (closed)', color.rgb(250, 200, 40)),
]


class GameHUD(Entity):
    """actions: callbacks 'new_game', 'restart', 'hint', 'solve' (gets an algorithm name), 'pause'.
    new_label names the 'new_game' button (Free Play calls it Levels: it goes back to level select)."""

    def __init__(self, actions, keys=None, new_label='New Game'):
        super().__init__(parent=camera.ui, z=-.05)
        self.actions = actions
        a = window.aspect_ratio / 2
        m = .03
        self.bar = w.HUDBar(parent=self, x=-a + m, y=.5 - m - w.HUDBar.H / 2)
        self.tip = None

        bh = theme.BUTTON_H * .82
        y = .5 - m - bh / 2
        x = a - m
        self.toolbar = Entity(parent=self)
        pause = w.icon_button(lambda p, s, c, **k: icons.pause(p, s, c, **k), self._act('pause'),
                              parent=self.toolbar, x=x - bh / 2, y=y, size=bh, key='Esc')
        x -= bh + .012
        specs = [('Solve', 'solve_menu', .13, None), ('Hint', 'hint', .14, 'H'), ('Restart', 'restart', .19, 'R'),
                 (new_label, 'new_game', .18, None)]
        self.buttons = {'pause': pause}
        for text, key, bw, shortcut in specs:
            b = w.UIButton(text, self._toggle_solve if key == 'solve_menu' else self._act(key),
                           parent=self.toolbar, x=x - bw / 2, y=y, w=bw, h=bh, size=theme.SMALL * 1.05,
                           marker=None, key=shortcut)
            self.buttons[key] = b
            x -= bw + .012
        self.bar_max_width = x + .012 - .02 - self.bar.x
        self.solve_menu = None

        self.legend = Entity(parent=self)
        self.status = None
        self.custom_keys = keys
        self.keys = w.KeyHint(keys or self._play_keys(False), parent=self)
        settings.on_change(self._setting)

    # ---- content ----
    def set(self, name, stats):
        self.bar.set(name, stats)
        self.bar.scale = min(1.0, self.bar_max_width / self.bar.width)
        if self.tip is not None:
            self._place_tip()

    def set_tip(self, text):
        if self.tip is not None:
            destroy(self.tip)
            self.tip = None
        if text:
            self.tip = Entity(parent=self)
            t = w.label(self.tip, text, theme.SMALL, theme.TEXT, theme.FONT_BODY, origin=(-.5, .5), wordwrap=40,
                        x=.02, y=-.016, z=-.002)
            h = t.height + .032
            wd = max(t.width, .1) + .04
            w.plate(self.tip, wd + 2 * theme.RIM_W, h + 2 * theme.RIM_W, theme.PANEL_RIM, shade=False,
                    x=wd / 2, y=-h / 2, z=.002)
            w.plate(self.tip, wd, h, theme.PANEL, shade=False, x=wd / 2, y=-h / 2, z=.001)
            w.plate(self.tip, .005, h - .012, theme.GOLD, 0, shade=False, x=.006, y=-h / 2, z=-.001)
            self._place_tip()

    def _place_tip(self):
        self.tip.x = self.bar.x
        self.tip.y = self.bar.y - w.HUDBar.H / 2 - .016

    @staticmethod
    def _play_keys(split):
        """Space only matters on levels with a split switch, where it swaps between the two cubes."""
        return [('arrows', 'Roll')] + ([('Space', 'Switch cube')] if split else []) +                [('R', 'Restart'), ('H', 'Hint'), ('Esc', 'Pause')]

    def set_split(self, on):
        if not self.custom_keys:
            self.keys.set(self._play_keys(on))

    def set_legend(self, kinds):
        """kinds: the GameSession.tile_at names present on this level."""
        destroy(self.legend)
        self.legend = Entity(parent=self)
        rows = [(label, col) for kind, label, col in LEGEND if kind in kinds]
        if not rows:
            return
        a = window.aspect_ratio / 2
        rh, pw = .03, .27
        ph = rh * len(rows) + .05
        panel = w.Panel(pw, ph, parent=self.legend, x=a - .03 - pw / 2, y=-.5 + .085 + ph / 2)
        for i, (label, col) in enumerate(rows):
            y = ph / 2 - .028 - i * rh
            w.plate(panel, .02, .02, col, .003, shade=False, x=-pw / 2 + .03, y=y, z=-.002)
            w.label(panel, label.upper(), theme.TINY, theme.TEXT, theme.FONT_LABEL, origin=(-.5, 0),
                    x=-pw / 2 + .052, y=y, z=-.002, max_width=pw - .07)
        self.legend.enabled = settings.get('legend')

    def set_status(self, text=None):
        """A pill above the key hints, e.g. 'BFS · move 3 / 31'. None hides it."""
        if self.status is not None:
            destroy(self.status)
            self.status = None
        if text:
            self.status = Entity(parent=self, y=-.405)
            t = w.label(self.status, text.upper(), theme.SMALL, theme.INK, theme.FONT_LABEL, z=-.002)
            w.plate(self.status, t.width + .05, .042, theme.GOLD, theme.CHAMFER, z=-.001)

    # ---- toolbar ----
    def _act(self, key):
        def run():
            self.close_solve_menu()
            fn = self.actions.get(key)
            if fn:
                fn()
        return run

    def _toggle_solve(self):
        if self.solve_menu is not None:
            self.close_solve_menu()
            return
        b = self.buttons['solve_menu']
        names = ORDER
        bh = theme.BUTTON_H * .78
        ph = len(names) * (bh + .01) + .03
        pw = .2
        self.solve_menu = w.Panel(pw, ph, parent=self, x=b.x + b.w / 2 - pw / 2,
                                  y=b.y - b.h / 2 - .02 - ph / 2)
        for i, name in enumerate(names):
            ready = implemented(name)
            b = w.UIButton(('Solve with ' if ready else 'No ') + SHORT[name] + ('' if ready else ' yet'),
                           (lambda n=name: self._solve(n)), parent=self.solve_menu,
                           y=ph / 2 - .015 - bh / 2 - i * (bh + .01), w=pw - .03, h=bh, size=theme.SMALL,
                           marker=None)
            b.disabled = not ready

    def _solve(self, name):
        self.close_solve_menu()
        fn = self.actions.get('solve')
        if fn:
            fn(name)

    def close_solve_menu(self):
        if self.solve_menu is not None:
            destroy(self.solve_menu)
            self.solve_menu = None

    def show(self, on):
        self.enabled = on
        if not on:
            self.close_solve_menu()

    def _setting(self, key, value):
        if key == 'legend':
            self.legend.enabled = value

    def on_destroy(self):
        settings.off(self._setting)
