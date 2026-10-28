"""Level select for Free Play (and the Algorithms lab): Normal / Advanced tabs, a grid of level tiles,
and a panel describing the chosen level.

Keeps everything the old Free Play menu did: the two level sets (tutorials first in Advanced), the
tutorial tips, ←/→ through the levels, Enter to start, Esc back.
"""
import json

from ursina import Entity, camera, color, destroy, window

from engine.catalog import LEVEL_DIR, TUTORIAL_LEVELS, TUTORIAL_TIPS, level_label, levels_for_mode
from .. import settings, theme
from .. import widgets as w

TILE_NAMES = {'f': 'fragile', 's': 'soft switch', 'h': 'heavy switch', 'v': 'split', 'l': 'bridge', 'r': 'bridge',
              'k': 'bridge', 'q': 'bridge'}
COLUMNS = 9


def level_features(level_number):
    """The advanced tile kinds a level uses, e.g. ['fragile', 'bridge', 'soft switch']."""
    try:
        data = json.loads((LEVEL_DIR / '{}.json'.format(level_number)).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    found = []
    for ch in ''.join(data.get('tiles', [])):
        name = TILE_NAMES.get(ch)
        if name and name not in found:
            found.append(name)
    return found


def tile_text(level_number):
    if level_number in TUTORIAL_LEVELS:
        return 'T{}'.format(TUTORIAL_LEVELS.index(level_number) + 1)
    return None


class LevelSelect(Entity):
    """on_start(level, mode) when a level is chosen; on_back() for Esc / Back."""

    def __init__(self, on_start, on_back, mode='normal', level=None, title='Free Play', action='Play'):
        super().__init__(parent=camera.ui, z=-.1)            # in front of the title shot's lettering
        self.on_start, self.on_back = on_start, on_back
        a = window.aspect_ratio / 2
        Entity(parent=self, model='quad', scale=(a * 2 + .1, 1.1), color=color.rgba(8, 9, 13, 200), z=.06)
        self.back = w.back_button(on_back, parent=self, x=-a + .14, y=.44)
        w.label(self, title.upper(), theme.HEADING, theme.TEXT, theme.FONT_TITLE, origin=(-.5, .5),
                x=-a + .06, y=.40)
        self.tabs = w.Tabs([('Normal', 'normal'), ('Advanced', 'advanced')], mode, self._mode, parent=self,
                           x=-a + .06 + .2, y=.25, w=.4)

        # info panel on the right
        pw, ph = .46, .62
        self.info = w.Panel(pw, ph, parent=self, x=a - .06 - pw / 2, y=-.02)
        p = self.info
        self.info_title = w.label(p, '', theme.HEADING * .9, theme.GOLD, theme.FONT_TITLE, origin=(-.5, .5),
                                  x=-pw / 2 + theme.PAD, y=ph / 2 - theme.PAD)
        self.info_state = w.label(p, '', theme.SMALL, theme.MUTED, theme.FONT_LABEL, origin=(-.5, .5),
                                  x=-pw / 2 + theme.PAD, y=ph / 2 - .115)
        w.line(p, pw - 2 * theme.PAD, y=ph / 2 - .155)
        self.info_tags = w.label(p, '', theme.SMALL, theme.TEXT, theme.FONT_LABEL, origin=(-.5, .5),
                                 x=-pw / 2 + theme.PAD, y=ph / 2 - .18)
        self.info_tip = w.label(p, '', theme.BODY, theme.MUTED, theme.FONT_BODY, origin=(-.5, .5),
                                x=-pw / 2 + theme.PAD, y=ph / 2 - .24)
        self.start = w.UIButton(action, self._start, parent=p, y=-ph / 2 + theme.PAD + theme.BUTTON_H / 2 + .004,
                                w=pw - 2 * theme.PAD, kind='primary', key='Enter', marker=None)

        self.grid = None
        self.mode = mode
        self.level = level
        self._build_grid()
        w.KeyHint([('arrows', 'Choose'), ('Enter', action), ('Tab', 'Normal / Advanced'), ('Esc', 'Back')],
                  parent=self)

    # ---- grid ----
    def _build_grid(self):
        if self.grid is not None:
            destroy(self.grid)
        a = window.aspect_ratio / 2
        self.grid = Entity(parent=self)
        self.levels = levels_for_mode(self.mode)
        if self.level not in self.levels:
            self.level = self.levels[0] if self.levels else None
        self.group = w.FocusGroup(grid_columns=COLUMNS, wrap=False)
        size, gap = .082, .028
        x0, y0 = -a + .06 + size / 2 + theme.FOCUS_W, .13
        self.tiles = {}
        for i, n in enumerate(self.levels):
            r, c = divmod(i, COLUMNS)
            t = w.LevelTile(n, self._pick, 'done' if settings.is_completed(n) else 'open', n == self.level,
                            parent=self.grid, x=x0 + c * (size + gap), y=y0 - r * (size + gap + .03), size=size,
                            caption=False, group=self.group, text=tile_text(n), on_focus=self._select)
            self.tiles[n] = t
        if self.level in self.tiles:
            self.group.focus(self.tiles[self.level])
        self._describe()

    def _mode(self, mode):
        self.mode = mode
        self.level = None
        self._build_grid()

    def _select(self, level_number):
        if level_number == self.level:
            return
        old = self.tiles.get(self.level)
        if old:
            old.set(selected=False)
        self.level = level_number
        self.tiles[level_number].set(selected=True)
        self._describe()

    def _pick(self, level_number):
        self._select(level_number)
        self._start()

    def _describe(self):
        n = self.level
        if n is None:
            return
        self.info_title.text = level_label(n).upper()
        w.fit(self.info_title, self.info.w - 2 * theme.PAD)
        self.info_state.text = ('COMPLETED' if settings.is_completed(n) else 'NOT CLEARED YET') + \
            '   ·   {} OF {}'.format(self.levels.index(n) + 1, len(self.levels))
        feats = level_features(n)
        self.info_tags.text = ('TILES:  ' + '  ·  '.join(f.upper() for f in feats)) if feats else 'PLAIN FLOOR AND VOID'
        w.fit(self.info_tags, self.info.w - 2 * theme.PAD)
        tip = TUTORIAL_TIPS.get(n) or 'Roll the block onto the goal hole standing upright.'
        self.info_tip.wordwrap = 0
        self.info_tip.text = tip
        self.info_tip.wordwrap = 30

    def _start(self):
        if self.level is not None:
            self.on_start(self.level, self.mode)

    def input(self, key):
        if w.Modal.busy():
            return
        if key == 'escape':
            self.on_back()
        elif key == 'tab':
            self.tabs.step(1)
        elif key in ('enter', 'space'):
            self._start()
        else:
            self.group.input(key)

    def close(self):
        destroy(self)
