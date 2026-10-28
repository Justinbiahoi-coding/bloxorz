"""Main menu over the city backdrop: title on the left, one control panel, key hints along the bottom."""
from ursina import Entity, application, camera, color, destroy, window

from .. import theme
from .. import widgets as w


class MainMenu(Entity):
    """actions: dict with 'tower', 'free_play', 'algorithms', 'settings' callbacks; Exit asks first."""

    def __init__(self, actions):
        super().__init__(parent=camera.ui)
        self.actions = actions
        a = window.aspect_ratio / 2
        left = -a + .09
        # shade the left of the picture so the panel reads over the bright street
        Entity(parent=self, model='quad', texture='horizontal_gradient', scale=(a * 1.3, 1),
               x=-a + a * .65, color=color.rgba(8, 9, 13, 225), z=.05)
        Entity(parent=self, model='quad', texture='vignette', scale=(a * 2, 1), color=color.rgba(0, 0, 0, 150),
               z=.04)

        title = w.label(self, 'BLOXORZ', theme.TITLE, theme.TEXT, theme.FONT_TITLE, origin=(-.5, .5),
                        x=left, y=.43)
        w.label(self, 'T O W E R', theme.SUBHEAD * 1.55, theme.GOLD, theme.FONT_TITLE, origin=(-.5, .5),
                x=left + .008, y=title.y - title.height * .8)

        bw, bh = .36, theme.BUTTON_H
        rows = [('Tower', 'tower', 'primary'), ('Free Play', 'free_play', 'secondary'),
                ('Algorithms', 'algorithms', 'secondary'), ('Settings', 'settings', 'secondary'),
                ('Exit', None, 'quiet')]
        gap = bh + .026
        ph = gap * len(rows) + .03
        panel = w.Panel(bw + .07, ph, parent=self, x=left + (bw + .07) / 2 + .02, y=.07 - ph / 2 + .02)
        self.group = w.FocusGroup()
        top = ph / 2 - .03 - bh / 2
        for i, (text, key, kind) in enumerate(rows):
            action = self._exit if key is None else (lambda k=key: self._go(k))
            w.UIButton(text, action, parent=panel, y=top - i * gap, w=bw, kind=kind, group=self.group)
        self.group.focus_first()

        w.label(self, 'CSC14003  ·  INTRODUCTION TO AI  ·  PROJECT 1', theme.TINY, theme.MUTED, theme.FONT_LABEL,
                origin=(.5, 0), x=a - .04, y=-.462)
        w.KeyHint([('updown', 'Select'), ('Enter', 'Confirm'), ('F', 'Fullscreen'), ('Esc', 'Exit')],
                  parent=self, x=-.12)

    def _go(self, key):
        fn = self.actions.get(key)
        if fn:
            fn()

    def _exit(self):
        w.ConfirmDialog('Quit Bloxorz Tower?', 'You can pick up any floor again from Free Play.',
                        application.quit, confirm='Quit', cancel='Stay')

    def input(self, key):
        if w.Modal.any_open():
            return
        if key == 'escape':
            self._exit()
        else:
            self.group.input(key)

    def close(self):
        destroy(self)
