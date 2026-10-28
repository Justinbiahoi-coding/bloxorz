"""Settings: music, move speed, fullscreen, key hints, tile legend, and clearing Free Play progress.

Opens as a dialog over whatever is behind it (the main menu or a paused game); every change is
applied and saved at once, so Back simply closes it.
"""
from ursina import window

from .. import block, settings, theme
from .. import widgets as w


def apply_all():
    """Push the stored settings into the running game (called at start-up and after each change)."""
    block.SPEED = settings.get('move_speed')
    if window.fullscreen != settings.get('fullscreen'):
        window.fullscreen = settings.get('fullscreen')


class SettingsScreen(w.Modal):
    def __init__(self, on_close=None):
        rows = 6
        h = .16 + rows * (theme.BUTTON_H + .016) + theme.BUTTON_H
        super().__init__(w=.66, h=h, title='Settings')
        self.on_close = on_close
        p = self.panel
        rw = .58
        y = p.content_top - theme.BUTTON_H / 2 - .004
        step = theme.BUTTON_H + .016
        self.group = w.FocusGroup()
        w.Slider('Music', settings.get('music'), lambda v: settings.set('music', round(v, 2)),
                 parent=p, y=y, w=rw, group=self.group)
        w.ChoiceRow('Move speed', settings.SPEEDS, settings.get('move_speed'), self._speed,
                    fmt=lambda v: '{:g}x'.format(v), parent=p, y=y - step, w=rw, group=self.group)
        w.Checkbox('Fullscreen', settings.get('fullscreen'), self._fullscreen, parent=p, y=y - 2 * step, w=rw,
                   group=self.group)
        w.Checkbox('Key hints', settings.get('key_hints'), lambda v: settings.set('key_hints', v),
                   parent=p, y=y - 3 * step, w=rw, group=self.group)
        w.Checkbox('Tile legend', settings.get('legend'), lambda v: settings.set('legend', v),
                   parent=p, y=y - 4 * step, w=rw, group=self.group)
        self.reset = w.UIButton('Clear Free Play progress', self._ask_reset, parent=p, y=y - 5 * step, w=rw,
                                kind='danger', group=self.group)
        self.reset.disabled = not settings.get('completed')       # nothing to forget yet
        self.back_button = w.UIButton('Back', self.close, parent=p, y=-h / 2 + theme.PAD + theme.BUTTON_H / 2 + .004,
                               w=rw, kind='primary', key='Esc', group=self.group)
        self.group.focus_first()

    def _speed(self, value):
        settings.set('move_speed', value)
        apply_all()

    def _fullscreen(self, value):
        settings.set('fullscreen', value)
        apply_all()

    def _ask_reset(self):
        n = len(settings.get('completed'))
        if not n or len(w.Modal.stack) > 1:
            return
        w.ConfirmDialog('Clear progress?', 'Forget the {} Free Play level{} marked as completed.'.format(
            n, '' if n == 1 else 's'), self._reset, confirm='Clear', danger=True)

    def _reset(self):
        settings.set('completed', [])
        w.Toast('Free Play progress cleared')
        if self:
            self.reset.disabled = True
            self.group.focus(self.back_button)

    def input(self, key):
        if not self.has_keys():                # a confirm dialog on top has the keys
            return
        if key == 'escape':
            self.close()
        else:
            self.group.input(key)

    def close(self):
        super().close()
        if self.on_close:
            self.on_close()
