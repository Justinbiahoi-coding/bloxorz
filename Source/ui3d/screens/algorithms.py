"""Algorithms lab: pick a stage and a search algorithm, run it from the stage's start, read the four
metrics the report needs (time, peak memory, expanded nodes, solution length), compare all solvers on
the same stage, and replay either the solution or the order the nodes were expanded on the 3D board.

Left column: setup, result cards, comparison table. Right: the level, with playback controls under it.
"""
from ursina import Entity, Vec3, camera, color, destroy, invoke, time, window

from engine import ALGORITHM_NAMES, GameSession, solve
from engine.catalog import levels_for_mode, level_label
from engine.problem import DIRS
from .. import icons, settings, theme
from .. import widgets as w
from ..block import Block
from ..floor import TILE_TOP, Floor
from ..hud import ORDER, SHORT
from ..world import aim_sun, move_lantern, point_camera
from .level_select import level_features

SKY = (14, 17, 34)


def fmt_time(ms):
    return '{:.1f} ms'.format(ms) if ms < 1000 else '{:.2f} s'.format(ms / 1000)


def fmt_memory(kb):
    if kb is None:
        return '—'
    return '{:.0f} KB'.format(kb) if kb < 1024 else '{:.1f} MB'.format(kb / 1024)


def fmt_int(n):
    return '{:,}'.format(n).replace(',', ' ')


def _state(item):
    return item.state if hasattr(item, 'state') else item     # BFS/UCS list nodes, DFS/A* list states


class AlgorithmsLab(Entity):
    def __init__(self, sun, on_back):
        super().__init__()
        self.sun, self.on_back = sun, on_back
        self.mode = 'normal'
        self.levels = levels_for_mode(self.mode)
        self.level = self.levels[0]
        self.algorithm = 'BFS'
        self.results = {}           # algorithm -> SolveResult (or an error string) for the current level
        self.session = self.floor = None
        self.block = Block()
        self.play = None            # current playback: dict(kind, states, actions, i, running)
        self.heat = {}
        self.heat_root = None
        self.ui = Entity(parent=camera.ui)
        self._build_ui()
        self._load_level()

    # ------------------------------------------------------------------ layout
    def _build_ui(self):
        a = window.aspect_ratio / 2
        L = -a + .03
        cw = .52                                           # left column width
        cx = L + cw / 2
        ui = self.ui
        gap, row = .012, theme.BUTTON_H
        inner = cw - 2 * theme.PAD
        w.back_button(self._back, parent=ui, x=L + .1, y=.465)
        w.label(ui, 'ALGORITHMS', theme.SUBHEAD * 1.45, theme.TEXT, theme.FONT_TITLE, origin=(-.5, 0),
                x=L + .25, y=.462)

        # setup: level set, stage, solver, run
        top = .425
        sh = .37
        setup = w.Panel(cw, sh, parent=ui, x=cx, y=top - sh / 2, title='Stage and solver', small=True)
        y = setup.content_top - row * .82 / 2
        self.tabs = w.Tabs([('Normal', 'normal'), ('Advanced', 'advanced')], self.mode, self._mode, parent=setup,
                           y=y, w=inner)
        y -= row * .82 / 2 + gap + row / 2
        self.stepper = w.Stepper('', self._step_level, parent=setup, y=y, w=inner, sub='')
        y -= row / 2 + gap + row * .82 / 2
        names = [(SHORT[n], n) for n in ORDER if n in ALGORITHM_NAMES]
        self.algo_tabs = w.Tabs(names, self.algorithm, self._pick_algorithm, parent=setup, y=y, w=inner)
        bw = (inner - theme.PAD) / 2
        by = -sh / 2 + theme.PAD * .7 + row / 2 + theme.DEPTH
        self.run_button = w.UIButton('Run', self.run, parent=setup, x=-bw / 2 - theme.PAD / 2, y=by, w=bw,
                                     kind='primary', key='Enter', marker=None)
        w.UIButton('Run all', self.run_all, parent=setup, x=bw / 2 + theme.PAD / 2, y=by, w=bw, key='A',
                   marker=None)

        # result of the selected algorithm
        top -= sh + .02
        rh = .265
        self.result_panel = w.Panel(cw, rh, parent=ui, x=cx, y=top - rh / 2, title='Result', small=True)
        rp = self.result_panel
        card_w = (inner - 3 * .01) / 4
        self.cards = {}
        for i, (key, caption) in enumerate([('time', 'Time'), ('memory', 'Peak memory'), ('expanded', 'Expanded'),
                                            ('length', 'Moves')]):
            self.cards[key] = w.StatCard(caption, '—', parent=rp, w=card_w, h=.09,
                                         x=-inner / 2 + card_w / 2 + i * (card_w + .01),
                                         y=rp.content_top - .045)
        self.result_note = w.label(rp, '', theme.TINY, theme.MUTED, theme.FONT_LABEL, origin=(-.5, .5),
                                   x=-inner / 2, y=rp.content_top - .1, z=-.002)
        bh = row * .8
        by = -rh / 2 + theme.PAD * .7 + bh / 2 + theme.DEPTH
        self.replay_button = w.UIButton('Replay solution', self.replay_solution, parent=rp,
                                        x=-bw / 2 - theme.PAD / 2, y=by, w=bw, h=bh, size=theme.SMALL,
                                        key='S', marker=None)
        self.explored_button = w.UIButton('Show explored', self.replay_explored, parent=rp,
                                          x=bw / 2 + theme.PAD / 2, y=by, w=bw, h=bh, size=theme.SMALL,
                                          key='N', marker=None)

        # comparison of every solver on this stage
        top -= rh + .02
        ch = top + .47
        self.compare = w.Panel(cw, ch, parent=ui, x=cx, y=top - ch / 2, title='Compare on this stage', small=True)
        self.compare_rows = Entity(parent=self.compare)

        # playback bar under the board
        px = (L + cw + a) / 2 + .01
        pw = min(.86, a - (L + cw) - .06)
        self.player = w.Panel(pw, .085, parent=ui, x=px, y=-.37)
        pp = self.player
        ib = theme.BUTTON_H * .8
        mk = lambda f: (lambda p, s, c, **k: f(p, s, c, **k))
        x0 = -pw / 2 + theme.PAD * .6 + ib / 2
        w.UIButton('', lambda: self.step(-1), parent=pp, x=x0, w=ib, h=ib, marker=None,
                   icon=lambda p, s, c, **k: icons.step(p, s, c, True, **k))
        self.play_button = w.UIButton('', self.toggle_play, parent=pp, x=x0 + ib + .008, w=ib, h=ib, marker=None,
                                      kind='primary', icon=mk(icons.triangle))
        w.UIButton('', lambda: self.step(1), parent=pp, x=x0 + 2 * (ib + .008), w=ib, h=ib, marker=None,
                   icon=lambda p, s, c, **k: icons.step(p, s, c, False, **k))
        self.play_label = w.label(pp, '', theme.SMALL, theme.TEXT, theme.FONT_LABEL, origin=(-.5, 0),
                                  x=x0 + 2.5 * (ib + .008) + .01, y=.013, z=-.002)
        bar_x0 = x0 + 2.5 * (ib + .008) + .01
        self.bar = w.ProgressBar('', parent=pp, x=(bar_x0 + pw / 2 - theme.PAD * .6) / 2, y=-.024,
                                 w=pw / 2 - theme.PAD * .6 - bar_x0)
        self.bar.caption.enabled = self.bar.amount.enabled = False
        self.player.enabled = False

        w.KeyHint([('leftright', 'Step'), ('Space', 'Play / pause'), ('Enter', 'Run'), ('A', 'Run all'),
                   ('Esc', 'Back')], parent=ui, x=.25)

    # ------------------------------------------------------------------ level
    def _mode(self, mode):
        self.mode = mode
        self.levels = levels_for_mode(mode)
        self.level = self.levels[0]
        self._load_level()

    def _step_level(self, step):
        i = (self.levels.index(self.level) + step) % len(self.levels)
        self.level = self.levels[i]
        self._load_level()

    def _load_level(self):
        self._stop_playback()
        self.results = {}
        if self.floor is not None:
            self.floor.destroy()
        self.session = GameSession(self.level)
        self.floor = Floor(self.session, 0, 1, free_play=True)
        self.block.place(self.session, self.session.state, self.floor.base)
        feats = level_features(self.level)
        self.stepper.value = level_label(self.level)
        self.stepper.sub = ' · '.join(feats) if feats else 'plain floor'
        self._aim()
        self._show_result()
        self._show_compare()

    def _aim(self):
        """Frame the whole playfield (and the lift over the goal) in the space right of the panels, above
        the playback bar: start from the usual steep view, then nudge and zoom until it fits."""
        import builtins
        import math
        from panda3d.core import Point2, Point3
        f = self.floor
        bx0, by0, bx1, by1 = f.bbox
        pts = [Point3(*f.at(x, y, h)) for x in (bx0 - .6, bx1 + .6) for y in (by0 - .6, by1 + .6) for h in (0, 2.8)]
        a = window.aspect_ratio / 2
        rx0, rx1 = (-a + .6) / a, (a - .04) / a            # target area in film units (-1..1)
        ry0, ry1 = -.56, .9
        view = Vec3(0, .87, -.5)
        target = Vec3(f.centre.x, f.base + .4, f.centre.z)
        dist = max(20.0, f.span * 1.6 + 10.0)
        camera.fov = 42
        out = Point2()
        for _ in range(30):
            camera.position = target + view * dist
            point_camera(camera, target)
            xs, ys = [], []
            for q in pts:
                camera.lens.project(camera.getRelativePoint(builtins.render, q), out)
                xs.append(out.x)
                ys.append(out.y)
            fx, fy = camera.lens.getFov()
            hx, hy = dist * math.tan(math.radians(fx / 2)), dist * math.tan(math.radians(fy / 2))
            ex = (min(xs) + max(xs)) / 2 - (rx0 + rx1) / 2
            ey = (min(ys) + max(ys)) / 2 - (ry0 + ry1) / 2
            ahead = Vec3(camera.forward.x, 0, camera.forward.z).normalized()
            target += camera.right * (ex * hx * .8) + ahead * (ey * hy * .9)
            dist *= max((max(xs) - min(xs)) / (rx1 - rx0), (max(ys) - min(ys)) / (ry1 - ry0)) ** .7
        camera.position = target + view * dist
        point_camera(camera, target)
        aim_sun(self.sun, f.centre)
        move_lantern(self.sun, f.centre)
        window.color = color.rgb(*SKY)

    # ------------------------------------------------------------------ running
    def _pick_algorithm(self, name):
        self.algorithm = name
        self._stop_playback()
        self._show_result()

    def run(self):
        self._stop_playback()
        self._busy('Running {}…'.format(SHORT[self.algorithm]))
        invoke(self._run_one, self.algorithm, True, delay=.05)     # let the message draw first

    def _run_one(self, name, show=True):
        try:
            self.results[name] = solve(self.level, name)
        except NotImplementedError:
            self.results[name] = 'not implemented'
        if show:
            self._busy(None)
            self._show_result()
            self._show_compare()

    def run_all(self):
        self._stop_playback()
        names = [n for n in ORDER if n in ALGORITHM_NAMES]

        def next_one(i=0):
            if i >= len(names) or not self:
                self._busy(None)
                self._show_result()
                self._show_compare()
                return
            self._busy('Running {} ({} / {})…'.format(SHORT[names[i]], i + 1, len(names)))
            invoke(lambda: (self._run_one(names[i], False), next_one(i + 1)), delay=.05)
        next_one()

    def _busy(self, text):
        if getattr(self, 'busy', None) is not None:
            destroy(self.busy)
            self.busy = None
        if text:
            self.busy = Entity(parent=self.ui, y=.02, x=self.player.x, z=-.1)
            t = w.label(self.busy, text, theme.LABEL, theme.INK, theme.FONT_LABEL, z=-.002)
            w.plate(self.busy, t.width + .06, .06, theme.GOLD, z=-.001)

    # ------------------------------------------------------------------ read-outs
    def _show_result(self):
        r = self.results.get(self.algorithm)
        self.result_panel.title.text = '{}  ·  {}'.format(SHORT[self.algorithm], level_label(self.level)).upper()
        solved = r is not None and not isinstance(r, str) and r.solved
        for b in (self.replay_button,):
            b.disabled = not solved
        self.explored_button.disabled = r is None or isinstance(r, str)
        if r is None:
            for card in self.cards.values():
                card.value = '—'
            self.result_note.text = 'Run a solver to see its numbers.'
            return
        if isinstance(r, str):
            for card in self.cards.values():
                card.value = '—'
            self.result_note.text = '{} is not implemented yet.'.format(self.algorithm)
            return
        self.cards['time'].value = fmt_time(r.elapsed_ms)
        self.cards['memory'].value = fmt_memory(r.peak_memory_kb)
        self.cards['expanded'].value = fmt_int(r.expanded)
        self.cards['length'].value = str(r.solution_length) if solved else '—'
        self.result_note.text = ('Solved from the stage start  ·  path cost {}'.format(r.solution_cost) if solved
                                 else 'No solution found.')

    def _show_compare(self):
        destroy(self.compare_rows)
        self.compare_rows = Entity(parent=self.compare)
        p = self.compare
        done = [(n, r) for n, r in ((n, self.results.get(n)) for n in ORDER) if r is not None]
        x0 = -p.w / 2 + theme.PAD
        cols = [('', 0), ('TIME', .07), ('MEMORY', .175), ('EXPANDED', .28), ('MOVES', .4)]
        if not done:
            w.label(self.compare_rows, 'Run all to compare the solvers here.', theme.SMALL, theme.MUTED,
                    theme.FONT_LABEL, origin=(-.5, .5), x=x0, y=p.content_top, z=-.002)
            return
        y = p.content_top - .004
        for text, cx in cols:
            w.label(self.compare_rows, text, theme.TINY * .9, theme.MUTED, theme.FONT_LABEL, origin=(-.5, .5),
                    x=x0 + cx, y=y, z=-.002)
        most = max((r.expanded for _, r in done if not isinstance(r, str)), default=1) or 1
        for i, (name, r) in enumerate(done):
            ry = y - .025 - i * .0205
            mine = name == self.algorithm
            col = theme.GOLD if mine else theme.TEXT
            w.label(self.compare_rows, SHORT[name], theme.TINY, col, theme.FONT_LABEL, origin=(-.5, .5), x=x0,
                    y=ry, z=-.002)
            if isinstance(r, str):
                w.label(self.compare_rows, 'not implemented', theme.TINY, theme.MUTED, theme.FONT_LABEL,
                        origin=(-.5, .5), x=x0 + cols[1][1], y=ry, z=-.002)
                continue
            vals = [fmt_time(r.elapsed_ms), fmt_memory(r.peak_memory_kb), fmt_int(r.expanded),
                    str(r.solution_length) if r.solved else '—']
            for (_, cx), v in zip(cols[1:], vals):
                w.label(self.compare_rows, v, theme.TINY, col, theme.FONT_LABEL, origin=(-.5, .5), x=x0 + cx,
                        y=ry, z=-.002)
            bar = .045 * r.expanded / most                         # expanded nodes as a bar, relative
            Entity(parent=self.compare_rows, model='quad', origin=(-.5, 0), x=x0 + .345, y=ry - .008,
                   scale=(max(.002, bar), .006), color=theme.GOLD if mine else theme.MUTED, z=-.002)

    # ------------------------------------------------------------------ playback
    def replay_solution(self):
        r = self.results.get(self.algorithm)
        if r is None or isinstance(r, str) or not r.solved:
            return
        path = r.solution_path()
        self._start_playback('solution', [n.state for n in path], r.goal_node.solution())

    def replay_explored(self):
        r = self.results.get(self.algorithm)
        if r is None or isinstance(r, str):
            return
        self._start_playback('explored', [_state(x) for x in r.explored], None)

    def _start_playback(self, kind, states, actions):
        self._stop_playback()
        self.play = dict(kind=kind, states=states, actions=actions, i=0, running=True, t=0.0, rolling=False,
                         budget=0.0)
        if kind == 'explored':
            self.heat_root = Entity(parent=self.floor.root)
            self.heat_root.setLightOff()
            self.heat = {}
        self.player.enabled = True
        self._show_state(0)
        self._update_player()

    def _stop_playback(self):
        if self.play and self.play.get('rolling'):
            self.block.finish()
        self.play = None
        if self.heat_root is not None:
            destroy(self.heat_root)
            self.heat_root = None
        self.heat = {}
        if self.session is not None and self.floor is not None:
            self.session.reset()
            self.floor.refresh()
            self.block.place(self.session, self.session.state, self.floor.base)
        if hasattr(self, 'player'):
            self.player.enabled = False

    def toggle_play(self):
        if not self.play:
            return
        p = self.play
        if p['i'] >= len(p['states']) - 1:          # at the end: play again from the start
            if p['kind'] == 'explored':
                self._start_playback('explored', p['states'], None)
                return
            p['i'] = 0
            self._show_state(0)
        p['running'] = not p['running']
        self._update_player()

    def step(self, d):
        if not self.play:
            return
        p = self.play
        if p.get('rolling'):
            self.block.finish()
            p['rolling'] = False
        p['running'] = False
        p['i'] = max(0, min(len(p['states']) - 1, p['i'] + d))
        if p['kind'] == 'explored' and d > 0:
            self._mark(p['states'][p['i']], p['i'])
        self._show_state(p['i'])
        self._update_player()

    def _show_state(self, i):
        state = self.play['states'][i]
        bridges_changed = state.bridges != self.session.state.bridges
        self.session.state = state
        if bridges_changed:
            self.floor.refresh()
        self.block.place(self.session, state, self.floor.base)
        if self.play['kind'] == 'explored' and i == 0:
            self._mark(state, 0)

    def _mark(self, state, i):
        """Light the cells of an expanded state; early nodes gold, later ones fading to blue."""
        n = max(1, len(self.play['states']) - 1)
        k = i / n
        col = color.rgba(int(255 - 160 * k), int(200 - 80 * k), int(90 + 140 * k), 150)
        for x, y in self.session.block_cells(state):
            q = self.heat.get((x, y))
            if q is None:
                q = Entity(parent=self.heat_root, model='quad', rotation_x=90, scale=.8,
                           position=self.floor.at(x, y, TILE_TOP + .02), color=col)
                self.heat[(x, y)] = q
            q.color = col

    def _update_player(self):
        p = self.play
        n = len(p['states']) - 1
        if p['kind'] == 'solution':
            self.play_label.text = 'SOLUTION  ·  MOVE {} / {}'.format(p['i'], n)
        else:
            self.play_label.text = 'EXPLORED  ·  NODE {} / {}  ·  {} CELLS'.format(
                fmt_int(p['i'] + 1), fmt_int(n + 1), len(self.heat))
        self.bar.set(p['i'] / max(1, n))
        icon = self.play_button.icon_entity
        destroy(icon)
        maker = icons.pause if p['running'] else icons.triangle
        self.play_button.icon_entity = maker(self.play_button.top, self.play_button.h * .42, theme.INK, z=-.003)

    def update(self):
        p = self.play
        if not p or not p['running']:
            return
        dt = time.dt
        if p['kind'] == 'solution':
            if p['rolling']:
                p['t'] += dt / self.block.duration
                self.block.set_progress(min(1.0, p['t']))
                if p['t'] >= 1:
                    self.block.finish()
                    p['rolling'] = False
                    p['i'] += 1
                    self.session.state = p['states'][p['i']]
                    self._update_player()
                return
            if p['i'] >= len(p['states']) - 1:
                p['running'] = False
                self._update_player()
                return
            before, after = p['states'][p['i']], p['states'][p['i'] + 1]
            action = p['actions'][p['i']]
            if before.bridges != after.bridges:
                self.session.state = after
                self.floor.refresh()
                self.session.state = before
            if action != 'SWITCH' and self.block.start_roll(self.session, before, after, action, DIRS[action],
                                                            self.floor.base):
                p['rolling'], p['t'] = True, 0.0
            else:
                p['i'] += 1
                self._show_state(p['i'])
                self._update_player()
        else:
            # explored: about eight seconds for the whole search at 1x, however many nodes it took
            n = len(p['states'])
            p['budget'] += dt * max(6.0, n / 8.0) * settings.get('move_speed')
            steps = int(p['budget'])
            if not steps:
                return
            p['budget'] -= steps
            last = min(n - 1, p['i'] + steps)
            for i in range(p['i'] + 1, last + 1):
                self._mark(p['states'][i], i)
            p['i'] = last
            self._show_state(last)
            if p['i'] >= n - 1:
                p['running'] = False
            self._update_player()

    # ------------------------------------------------------------------ input
    def input(self, key):
        if w.Modal.busy():
            return
        if key == 'escape':
            self._back()
        elif key == 'enter':
            self.run()
        elif key == 'a':
            self.run_all()
        elif key == 's':
            self.replay_solution()
        elif key == 'n':
            self.replay_explored()
        elif key == 'space':
            self.toggle_play()
        elif key in ('left arrow', 'right arrow'):
            self.step(-1 if key == 'left arrow' else 1)
        elif key in ('up arrow', 'down arrow'):
            self._step_level(-1 if key == 'up arrow' else 1)
        elif key == 'tab':
            self.tabs.step(1)

    def _back(self):
        self.on_back()

    def close(self):
        self._stop_playback()
        self.block.clear()
        if self.floor is not None:
            self.floor.destroy()
        destroy(self.ui)
        destroy(self)
