"""Loading screen: the title, a progress bar and what is being built.

run(steps, on_done) walks a generator of (fraction, caption) one step per frame. A scene is built in
one go, so building(key) also redraws the bar while it loads: every model load nudges the bar towards
the end, measured against how many loads that scene took last time.
"""
import time
from contextlib import contextmanager

from ursina import Entity, application, camera, destroy, invoke

from .. import loadfast, theme
from .. import widgets as w

# model loads per scene (the first build of a session goes by these, later ones by what they really took)
EXPECTED = {'title': 1330, 'tower': 1330, 'free_play': 230, 'lab': 270}


class LoadingScreen(Entity):
    def __init__(self, caption='Loading', **kw):
        super().__init__(parent=camera.ui, z=-.95, **kw)
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

    @contextmanager
    def building(self, key, start, end):
        """Move the bar from start towards end while the scene under construction loads its models."""
        expected = EXPECTED.get(key, 600)
        count, last = [0], [0.0]
        base = application.base

        def tick():
            count[0] += 1
            now = time.perf_counter()
            if now - last[0] < 1 / 30:
                return
            last[0] = now
            self.bar.set(start + (end - start) * min(.98, count[0] / expected))
            base.graphicsEngine.renderFrame()          # show it now: the build holds the frame loop

        loadfast.on_load = tick
        try:
            yield
        finally:
            loadfast.on_load = None
            if count[0]:
                EXPECTED[key] = count[0]

    def close(self):
        destroy(self)
