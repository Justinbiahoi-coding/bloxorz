"""Loading screen: the title, a progress bar and what is being built.

run(steps, on_done) walks a generator of (fraction, caption) one step per frame, so the bar
moves between the slow parts instead of freezing on a black window.
"""
from ursina import Entity, camera, destroy, invoke

from .. import theme
from .. import widgets as w


class LoadingScreen(Entity):
    def __init__(self, caption='Loading', **kw):
        super().__init__(parent=camera.ui, z=-.5, **kw)
        Entity(parent=self, model='quad', scale=(8, 2), color=theme.BG, z=.01)
        w.label(self, 'BLOXORZ', theme.TITLE * .7, theme.TEXT, theme.FONT_TITLE, y=.1)
        w.label(self, 'T O W E R', theme.SUBHEAD * 1.2, theme.GOLD, theme.FONT_TITLE, y=.02)
        self.bar = w.ProgressBar(caption, parent=self, y=-.12, w=.5)

    def run(self, steps, on_done):
        def advance():
            if not self:
                return
            try:
                fraction, caption = next(steps)
            except StopIteration:
                on_done()
                return
            self.bar.set(fraction, caption)
            invoke(advance, delay=.02)      # draw the bar before the next slow step
        invoke(advance, delay=.02)

    def close(self):
        destroy(self)
