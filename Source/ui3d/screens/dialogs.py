"""Pause menu and the end-of-level result, as dialogs over the paused game."""
from .. import theme
from .. import widgets as w


class _MenuDialog(w.Modal):
    """A titled dialog with a column of buttons; Esc runs the escape action."""

    def __init__(self, title, rows, subtitle=None, escape=None, keys=None, width=.46, title_col=theme.TEXT):
        bh, gap = theme.BUTTON_H, .016
        sub_h = .06 if subtitle else 0
        h = .11 + sub_h + len(rows) * (bh + gap)
        super().__init__(w=width, h=h, title=title)
        if title_col is not theme.TEXT and self.panel.title:
            self.panel.title.color = title_col
        p = self.panel
        y = p.content_top
        if subtitle:
            w.label(p, subtitle, theme.BODY, theme.MUTED, theme.FONT_LABEL, origin=(0, .5), y=y, z=-.002,
                    max_width=width - 2 * theme.PAD)
            y -= sub_h
        self.group = w.FocusGroup()
        for i, (text, action, kind, key) in enumerate(rows):
            w.UIButton(text, self._run(action), parent=p, y=y - bh / 2 - i * (bh + gap), w=width - 2 * theme.PAD,
                       kind=kind, key=key, group=self.group)
        self.group.focus_first()
        self.escape = escape
        self.keys = keys or {}

    def _run(self, action):
        def go():
            self.close()
            if action:
                action()
        return go

    def input(self, key):
        if not self.has_keys():
            return
        if key == 'escape':
            self.close()
            if self.escape:
                self.escape()
        elif key in self.keys:
            self._run(self.keys[key])()
        else:
            self.group.input(key)


class PauseMenu(_MenuDialog):
    """resume / restart / new_game / settings / main_menu callbacks."""

    def __init__(self, resume, restart, new_game, settings, main_menu, title='Paused', new_label='New Game'):
        super().__init__(title, [
            ('Resume', resume, 'primary', 'Esc'),
            ('Restart', restart, 'secondary', 'R'),
            (new_label, new_game, 'secondary', None),
            ('Settings', settings, 'secondary', None),
            ('Main Menu', main_menu, 'secondary', None),
        ], escape=resume, keys={'r': restart})


class ResultDialog(_MenuDialog):
    """Win: Next (if any), Retry, Levels, Main Menu. Fall: Retry, Levels, Main Menu.

    Keeps the old shortcuts: N or Enter next, R retry, Esc menu.
    """

    def __init__(self, won, moves, best=None, on_next=None, on_retry=None, on_levels=None, on_menu=None,
                 title=None, cost=None, cost_label='Cost'):
        rows = []
        keys = {'r': on_retry}
        if won and on_next:
            rows.append(('Next Level', on_next, 'primary', 'N'))
            keys['n'] = on_next
        rows.append(('Retry', on_retry, 'secondary' if rows else 'primary', 'R'))
        if on_levels:
            rows.append(('Level Select', on_levels, 'secondary', None))
        rows.append(('Main Menu', on_menu, 'secondary', 'Esc'))
        if won:
            sub = '{} moves'.format(moves)
            if cost is not None:
                sub += '   ·   {} {}'.format(cost_label.lower(), cost)
            if best is not None:
                sub += '\nbest possible {} moves'.format(best)
        else:
            sub = 'The block fell after {} moves'.format(moves)
        super().__init__(title or ('Level cleared' if won else 'You fell'), rows, subtitle=sub, escape=on_menu,
                         keys=keys, title_col=theme.GOLD if won else theme.ORANGE)
