"""Reusable 3D-UI pieces: panels, buttons, steppers, tabs, toggles, stat cards, key hints, toasts, modals.

All pieces live under camera.ui (height 1, width window.aspect_ratio) and take their look from theme.
Buttons work with the mouse and, through a FocusGroup, with the keyboard.
"""
from ursina import Entity, Quad, Text, camera, color, destroy, invoke

from . import icons, theme


def rounded(parent, w, h, col, corner=theme.CORNER, **kw):
    """A rounded rectangle of size (w, h) centred on the parent origin; corner is the radius in ui units."""
    radius = min(.5, corner / h)          # Quad measures the radius against the height
    return Entity(parent=parent, model=Quad(aspect=w / h, radius=radius), scale=(w, h), color=col, **kw)


def label(parent, text, size=theme.BODY, col=theme.TEXT, origin=(0, 0), **kw):
    t = Text(text, parent=parent, scale=size, color=col, origin=origin, **kw)
    t.use_tags = False          # show '<' and similar as plain text
    t.text = text
    return t


class Panel(Entity):
    """Dark glass panel with a faint gold outline. Put content under it; (0, 0) is its centre."""

    def __init__(self, w, h, parent=camera.ui, x=0, y=0, title=None, col=theme.PANEL, outline=True, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.w, self.h = w, h
        if outline:
            rounded(self, w + .006, h + .006, theme.LINE, corner=theme.CORNER + .003, z=.002)
        self.fill = rounded(self, w, h, col, z=.001)
        self.title = None
        if title:
            self.title = label(self, title.upper(), theme.SMALL, theme.GOLD, origin=(-.5, .5),
                               x=-w / 2 + .03, y=h / 2 - .025)

    def top(self, offset=0.0):
        """y of the panel's top edge, moved down by offset (and past the title if any)."""
        return self.h / 2 - offset - (.06 if self.title else 0)


class FocusGroup:
    """Keyboard focus over a list of buttons: arrows move, Enter/Space presses. The mouse moves it too."""

    def __init__(self, buttons=(), horizontal=False, wrap=True):
        self.buttons = []
        self.index = -1
        self.horizontal = horizontal
        self.wrap = wrap
        for b in buttons:
            self.add(b)

    def add(self, button):
        button.group = self
        self.buttons.append(button)
        return button

    def focus(self, button):
        for b in self.buttons:
            b.set_focus(b is button)
        self.index = self.buttons.index(button) if button in self.buttons else -1

    def move(self, step):
        live = [b for b in self.buttons if b.enabled and not b.disabled]
        if not live:
            return
        current = self.buttons[self.index] if 0 <= self.index < len(self.buttons) else None
        i = live.index(current) if current in live else (-1 if step > 0 else 0)
        i += step
        i = i % len(live) if self.wrap else max(0, min(len(live) - 1, i))
        self.focus(live[i])

    def input(self, key):
        """Handle a key; returns True if it was used."""
        back, fwd = ('left arrow', 'right arrow') if self.horizontal else ('up arrow', 'down arrow')
        if key == back:
            self.move(-1)
        elif key == fwd:
            self.move(1)
        elif key in ('enter', 'space') and 0 <= self.index < len(self.buttons):
            self.buttons[self.index].press()
        else:
            return False
        return True


class UIButton(Entity):
    """Rounded button. kind: 'primary' (gold), 'secondary' (navy) or 'danger' (orange).

    key: a short shortcut label drawn on the right ('Esc', 'R'...). The shortcut itself is
    handled by the screen; the label only tells the player about it.
    """

    COLORS = {
        'primary': (theme.GOLD, theme.GOLD_HOVER, theme.INK),
        'secondary': (theme.BTN, theme.BTN_HOVER, theme.TEXT),
        'danger': (theme.ORANGE, theme.ORANGE_HOVER, theme.INK),
    }

    def __init__(self, text, on_click=None, parent=camera.ui, x=0, y=0, w=.42, h=theme.BUTTON_H,
                 kind='secondary', key=None, size=theme.BODY, align='center', group=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.w, self.h = w, h
        self.kind = kind
        self.action = on_click
        self.group = None
        self.focused = False
        self._disabled = False
        base, _, ink = self.COLORS[kind]
        self.bg = rounded(self, w, h, base, corner=min(h * .32, theme.CORNER), collider='box')
        self.bg.on_click = self.press
        self.bg.on_mouse_enter = self._enter
        self.bg.on_mouse_exit = self._exit
        self.bar = Entity(parent=self, model='quad', scale=(.005, h * .5), color=theme.GOLD,
                          x=-w / 2 + .014, z=-.002, enabled=False)
        pad = .035
        if align == 'left':
            self.text_entity = label(self, text, size, ink, origin=(-.5, 0), x=-w / 2 + pad, z=-.003)
        else:
            self.text_entity = label(self, text, size, ink, z=-.003)
        self.key_entity = None
        if key:
            self.key_entity = label(self, key, theme.SMALL, theme.MUTED if kind == 'secondary' else ink,
                                    origin=(.5, 0), x=w / 2 - pad * .7, z=-.003)
        if group is not None:
            group.add(self)

    # ---- state ----
    @property
    def text(self):
        return self.text_entity.text

    @text.setter
    def text(self, value):
        self.text_entity.text = value

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._disabled = value
        base, _, ink = self.COLORS[self.kind]
        self.bg.color = theme.BTN_OFF if value else base
        self.text_entity.color = theme.MUTED if value else ink
        if value and self.focused:
            self.set_focus(False)

    def set_focus(self, on):
        self.focused = on and not self._disabled
        base, hover, _ = self.COLORS[self.kind]
        self.bg.color = hover if self.focused else (theme.BTN_OFF if self._disabled else base)
        self.bar.enabled = self.focused and self.kind == 'secondary'
        k = 1.03 if self.focused else 1.0
        self.bg.animate_scale((self.w * k, self.h * k), duration=theme.FAST)

    def press(self):
        if self._disabled or not self.enabled:
            return
        self.bg.scale = (self.w * .97, self.h * .97)
        self.bg.animate_scale((self.w, self.h), duration=theme.FAST)
        if self.action:
            invoke(self.action, delay=.03)    # let the press show before the screen changes

    # ---- mouse ----
    def _enter(self):
        if self.group:
            self.group.focus(self)
        else:
            self.set_focus(True)

    def _exit(self):
        if not self.group:
            self.set_focus(False)


class Stepper(Entity):
    """‹ value › picker. on_step(step) is called with -1 or +1; set .value to change the text."""

    def __init__(self, value='', on_step=None, parent=camera.ui, x=0, y=0, w=.5, h=theme.BUTTON_H,
                 size=theme.SUBHEAD, sub=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.on_step = on_step
        bw = h * 1.05
        self.prev = UIButton('‹', lambda: self._step(-1), parent=self, x=-w / 2 + bw / 2, w=bw, h=h,
                             size=theme.SUBHEAD)
        self.next = UIButton('›', lambda: self._step(1), parent=self, x=w / 2 - bw / 2, w=bw, h=h,
                             size=theme.SUBHEAD)
        self.value_text = label(self, value, size, theme.TEXT, y=.008 if sub is not None else 0)
        self.sub_text = label(self, sub or '', theme.SMALL, theme.MUTED, y=-.03)

    def _step(self, step):
        if self.on_step:
            self.on_step(step)

    @property
    def value(self):
        return self.value_text.text

    @value.setter
    def value(self, text):
        self.value_text.text = text

    @property
    def sub(self):
        return self.sub_text.text

    @sub.setter
    def sub(self, text):
        self.sub_text.text = text


class Tabs(Entity):
    """Segmented control. options: [(label, value)]; on_change(value)."""

    def __init__(self, options, value=None, on_change=None, parent=camera.ui, x=0, y=0, w=.5,
                 h=theme.BUTTON_H * .85, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.options = list(options)
        self.on_change = on_change
        rounded(self, w + .01, h + .01, theme.BTN_OFF, corner=h * .4, z=.001)
        seg = w / len(self.options)
        self.buttons = []
        for i, (text, val) in enumerate(self.options):
            b = UIButton(text, (lambda v=val: self.select(v, notify=True)), parent=self,
                         x=-w / 2 + seg * (i + .5), w=seg - .006, h=h, size=theme.BODY)
            self.buttons.append(b)
        self.value = None
        self.select(value if value is not None else self.options[0][1])

    def select(self, value, notify=False):
        self.value = value
        for b, (_, val) in zip(self.buttons, self.options):
            on = val == value
            b.kind = 'primary' if on else 'secondary'
            base, _, ink = UIButton.COLORS[b.kind]
            b.bg.color = base
            b.text_entity.color = ink
        if notify and self.on_change:
            self.on_change(value)

    def step(self, step):
        values = [v for _, v in self.options]
        i = (values.index(self.value) + step) % len(values)
        self.select(values[i], notify=True)


class Toggle(Entity):
    """A labelled on/off switch. on_change(bool)."""

    def __init__(self, text, value=False, on_change=None, parent=camera.ui, x=0, y=0, w=.6,
                 h=theme.BUTTON_H, group=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.on_change = on_change
        self.button = UIButton(text, self.flip, parent=self, w=w, h=h, align='left', group=group)
        self.track = rounded(self, h * 1.1, h * .5, theme.BTN_OFF, corner=h * .25, x=w / 2 - h * .8, z=-.004)
        self.knob = rounded(self, h * .4, h * .4, theme.TEXT, corner=h * .2, z=-.005)
        self.state_text = label(self, '', theme.SMALL, theme.MUTED, origin=(.5, 0),
                                x=w / 2 - h * 1.5, z=-.004)
        self.value = None
        self.set(value)

    def set(self, value, notify=False):
        self.value = bool(value)
        x0 = self.track.x
        self.knob.animate_x(x0 + (self.track.scale_x / 2 - self.knob.scale_x * .75) * (1 if value else -1),
                            duration=theme.FAST)
        self.track.color = theme.GOLD if value else theme.BTN_OFF
        self.state_text.text = 'ON' if value else 'OFF'
        if notify and self.on_change:
            self.on_change(self.value)

    def flip(self):
        self.set(not self.value, notify=True)


class StatCard(Panel):
    """One big number with a small caption under it."""

    def __init__(self, caption, value='—', parent=camera.ui, x=0, y=0, w=.2, h=.11, accent=theme.GOLD, **kw):
        super().__init__(w, h, parent=parent, x=x, y=y, col=theme.PANEL_SOLID, outline=False, **kw)
        self.value_text = label(self, value, theme.STAT, accent, y=.012, z=-.003)
        self.caption_text = label(self, caption.upper(), theme.SMALL * .85, theme.MUTED, y=-.034, z=-.003)

    @property
    def value(self):
        return self.value_text.text

    @value.setter
    def value(self, text):
        self.value_text.text = text


class KeyHint(Entity):
    """A row of key chips and what they do, e.g. [('arrows', 'roll'), ('R', 'restart')], centred at y."""

    CHIP_H = .03

    def __init__(self, items, parent=camera.ui, y=-.465, **kw):
        super().__init__(parent=parent, y=y, **kw)
        self.set(items)

    def set(self, items):
        for child in list(self.children):
            destroy(child)
        h = self.CHIP_H
        cursor = 0.0
        parts = []
        for keys, action in items:
            group = Entity(parent=self)
            x = 0.0
            for key in (('up', 'down', 'left', 'right') if keys == 'arrows' else (keys,)):
                if key in icons.ARROW_ANGLES:
                    w = h
                    rounded(group, w, h, theme.BTN, corner=h * .3, x=x + w / 2)
                    icons.arrow(group, h * .42, theme.TEXT, key, x=x + w / 2, z=-.001)
                else:
                    t = label(group, key, theme.SMALL * .9, theme.TEXT, z=-.001)
                    w = max(h, t.width + .018)
                    t.x = x + w / 2
                    rounded(group, w, h, theme.BTN, corner=h * .3, x=x + w / 2)
                x += w + .004
            t = label(group, action, theme.SMALL, theme.MUTED, origin=(-.5, 0), x=x + .006)
            x += .006 + t.width
            group.x = cursor
            parts.append(group)
            cursor += x + .035
        total = cursor - .035
        for g in parts:
            g.x -= total / 2


class Toast(Entity):
    """A short message that fades out by itself."""

    def __init__(self, text, parent=camera.ui, y=.36, duration=2.2, col=theme.TEXT, **kw):
        super().__init__(parent=parent, y=y, z=-.2, **kw)
        t = label(self, text, theme.BODY, col, z=-.001)
        self.box = rounded(self, t.width + .06, .055, theme.PANEL_SOLID, corner=.02)
        self.text_entity = t
        invoke(self._fade, delay=duration)

    def _fade(self):
        if not self:
            return
        for e in (self.box, self.text_entity):
            e.animate_color(color.clear, duration=.3)
        destroy(self, delay=.35)


class Modal(Entity):
    """A veil over everything with a panel in the middle; .panel is where content goes."""

    def __init__(self, w=.7, h=.6, title=None, parent=camera.ui, **kw):
        super().__init__(parent=parent, z=-.1, **kw)
        self.veil = Entity(parent=self, model='quad', scale=(4, 2), color=theme.DIM, z=.01, collider='box')
        self.panel = Panel(w, h, parent=self, title=title)
        self.panel.scale = .94
        self.panel.animate_scale(1, duration=theme.MEDIUM)
