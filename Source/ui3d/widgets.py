"""Reusable 3D-UI pieces in the elevator-panel style.

Everything lives under camera.ui (height 1, width window.aspect_ratio) and takes its look from theme.
Focusable pieces (buttons, level tiles, sliders, checkboxes) share one protocol so a FocusGroup can
drive them from the keyboard: set_focus(on), press(), .disabled, .enabled, .group.

Labels shrink to fit the space they are given, so nothing is cut off at 1280x720 or 1920x1080.
"""
from ursina import Entity, Mesh, Text, Vec3, camera, color, destroy, invoke, mouse

from . import icons, theme


# ---------------------------------------------------------------- primitives

def plate(parent, w, h, col, chamfer=theme.CHAMFER, shade=True, **kw):
    """A rectangle with chamfered corners, centred on the parent origin. shade adds a soft top light."""
    c = min(chamfer, w / 2, h / 2)
    x, y = w / 2, h / 2
    ring = [(-x + c, -y), (x - c, -y), (x, -y + c), (x, y - c), (x - c, y), (-x + c, y), (-x, y - c), (-x, -y + c)]
    verts = [(0, 0)] + ring
    tris = [(0, i, i + 1) for i in range(1, 8)] + [(0, 8, 1)]
    colors = None
    if shade:
        colors = [(s, s, s, 1) for s in [.92] + [.82 + .18 * ((py + y) / h) for _, py in ring]]
    mesh = Mesh(vertices=[Vec3(px, py, 0) for px, py in verts], triangles=tris, colors=colors, mode='triangle')
    return Entity(parent=parent, model=mesh, color=col, **kw)


def label(parent, text, size=theme.BODY, col=theme.TEXT, font=theme.FONT_BODY, origin=(0, 0),
          max_width=None, **kw):
    """Plain text (no Ursina tags). With max_width it shrinks until it fits; wordwrap is in characters."""
    wrap = kw.pop('wordwrap', None)
    t = Text('', parent=parent, scale=size, color=col, origin=origin, font=font, **kw)
    t.use_tags = False
    t.resolution = theme.RESOLUTION.get(font, 96)
    t.text = text
    if wrap:
        t.wordwrap = wrap               # Ursina only wraps text that is already there
    fit(t, max_width)
    return t


def fit(text_entity, max_width):
    if max_width and text_entity.text and text_entity.width > max_width:
        text_entity.scale *= max_width / text_entity.width
    return text_entity


def line(parent, w, col=theme.DIVIDER, thickness=.0018, **kw):
    return Entity(parent=parent, model='quad', scale=(w, thickness), color=col, **kw)


# ---------------------------------------------------------------- focus

class FocusGroup:
    """Keyboard focus over focusable pieces: arrows move, Enter/Space presses. The mouse moves it too."""

    def __init__(self, items=(), horizontal=False, wrap=True, grid_columns=None):
        self.items = []
        self.index = -1
        self.horizontal = horizontal
        self.wrap = wrap
        self.columns = grid_columns          # set for a grid: left/right step 1, up/down step a row
        for item in items:
            self.add(item)

    def add(self, item):
        item.group = self
        self.items.append(item)
        return item

    @property
    def current(self):
        return self.items[self.index] if 0 <= self.index < len(self.items) else None

    def focus(self, item):
        for other in self.items:
            if other is not item and other.focused:
                other.set_focus(False)
        if item is not None and not item.disabled:
            item.set_focus(True)
            self.index = self.items.index(item)

    def focus_first(self):
        for item in self.items:
            if item.enabled and not item.disabled:
                self.focus(item)
                return

    def move(self, step):
        live = [i for i in self.items if i.enabled and not i.disabled]
        if not live:
            return
        cur = self.current
        i = live.index(cur) if cur in live else (-1 if step > 0 else len(live))
        i += step
        if self.wrap:
            i %= len(live)
        else:
            i = max(0, min(len(live) - 1, i))
        self.focus(live[i])

    def input(self, key):
        """Handle a key; returns True if it was used."""
        cur = self.current
        if cur is not None and hasattr(cur, 'take_key') and cur.take_key(key):
            return True
        if self.columns:
            steps = {'left arrow': -1, 'right arrow': 1, 'up arrow': -self.columns, 'down arrow': self.columns}
        elif self.horizontal:
            steps = {'left arrow': -1, 'right arrow': 1}
        else:
            steps = {'up arrow': -1, 'down arrow': 1}
        if key in steps:
            if self.current is None:
                self.focus_first()
            else:
                self.move(steps[key])
            return True
        if key in ('enter', 'space') and cur is not None:
            cur.press()
            return True
        return False


class _Focusable(Entity):
    """Shared state for anything a FocusGroup can drive."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.group = None
        self.focused = False
        self.hovered_ = False
        self._disabled = False

    @property
    def disabled(self):
        return self._disabled

    @disabled.setter
    def disabled(self, value):
        self._disabled = bool(value)
        if value:
            self.focused = self.hovered_ = False
        self.refresh()

    def set_focus(self, on):
        self.focused = bool(on) and not self._disabled
        self.refresh()

    def _enter(self):
        if self._disabled:
            return
        self.hovered_ = True
        if self.group:
            self.group.focus(self)
        self.refresh()

    def _exit(self):
        self.hovered_ = False
        self.refresh()

    def _hook(self, target):
        """Route the mouse on target (an entity with a collider) to this piece."""
        target.on_click = self.press
        target.on_mouse_enter = self._enter
        target.on_mouse_exit = self._exit

    def refresh(self):
        pass

    def press(self):
        pass


# ---------------------------------------------------------------- buttons

class UIButton(_Focusable):
    """Chamfered plate button.

    kind: 'primary' (gold, the one main action), 'secondary' (charcoal), 'quiet' (text only, e.g. Exit)
          or 'danger' (charcoal with orange text, for things that throw progress away).
    key: a shortcut label drawn on the right ('Esc', 'R'); the screen handles the key itself.
    marker: where the gold focus pointer sits, 'left' (vertical menus), 'below' (rows) or None.
    icon: a function (parent, size, colour) -> Entity from ui3d.icons, drawn instead of / before text.
    """

    KINDS = {
        'primary': dict(face=theme.GOLD, hover=theme.GOLD_HOVER, press=theme.GOLD_PRESS,
                        edge=theme.GOLD_EDGE, rim=theme.GOLD_EDGE, ink=theme.INK),
        'secondary': dict(face=theme.FACE, hover=theme.FACE_HOVER, press=theme.FACE_PRESS,
                          edge=theme.EDGE, rim=theme.RIM, ink=theme.TEXT),
        'danger': dict(face=theme.FACE, hover=theme.FACE_HOVER, press=theme.FACE_PRESS,
                       edge=theme.EDGE, rim=theme.RIM, ink=theme.ORANGE),
        'quiet': dict(face=color.clear, hover=color.clear, press=color.clear,
                      edge=color.clear, rim=color.clear, ink=theme.TEXT),
    }

    def __init__(self, text='', on_click=None, parent=camera.ui, x=0, y=0, w=.34, h=theme.BUTTON_H,
                 kind='secondary', key=None, size=theme.LABEL, align='center', marker='left',
                 group=None, icon=None, upper=True, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.w, self.h, self.kind, self.action = w, h, kind, on_click
        self.marker_side = marker
        self.pressed = False
        k = self.KINDS[kind]
        fw = theme.FOCUS_W
        self.ring = plate(self, w + 2 * fw, h + theme.DEPTH + 2 * fw, theme.GOLD_RIM, shade=False,
                          y=-theme.DEPTH / 2, z=.004, enabled=False)
        self.rim = plate(self, w + 2 * theme.RIM_W, h + theme.DEPTH + 2 * theme.RIM_W, k['rim'], shade=False,
                         y=-theme.DEPTH / 2, z=.003)
        self.edge = plate(self, w, h, k['edge'], shade=False, y=-theme.DEPTH, z=.002)
        self.top = Entity(parent=self)
        self.face = plate(self.top, w, h, k['face'], z=.001, collider='box')
        self._hook(self.face)

        key_w = 0
        self.key_entity = None
        if key:
            self.key_entity = label(self.top, key, theme.SMALL, theme.MUTED, theme.FONT_LABEL,
                                    origin=(.5, 0), x=w / 2 - theme.PAD * .7, z=-.003)
            key_w = self.key_entity.width + theme.PAD * .5
        self.icon_entity = None
        icon_w = 0
        if icon:
            s = h * .42
            self.icon_entity = icon(self.top, s, k['ink'], z=-.003)
            icon_w = s + (.012 if text else 0)
        room = w - 2 * theme.PAD - key_w - icon_w
        shown = text.upper() if upper else text
        self.text_entity = label(self.top, shown, size, k['ink'], theme.FONT_LABEL, max_width=room, z=-.003,
                                 origin=(-.5, 0) if align == 'left' else (0, 0))
        if align == 'left':
            self.text_entity.x = -w / 2 + theme.PAD + icon_w
            if self.icon_entity:
                self.icon_entity.x = -w / 2 + theme.PAD + h * .21
        else:                                   # centre in the room left of the key label
            shift = -key_w / 2
            if self.icon_entity:
                total = icon_w + self.text_entity.width
                self.icon_entity.x = shift - total / 2 + h * .21
                self.text_entity.x = shift - total / 2 + icon_w + self.text_entity.width / 2
            else:
                self.text_entity.x = shift

        self.marker = None
        if marker == 'left':
            self.marker = icons.triangle(self, .018, theme.GOLD, x=-w / 2 - .024, z=-.003, enabled=False)
        elif marker == 'below':
            self.marker = icons.triangle(self, .016, theme.GOLD, -90, y=-h / 2 - theme.DEPTH - .02,
                                         z=-.003, enabled=False)
        self.underline = None
        if kind == 'quiet':
            self.underline = line(self.top, self.text_entity.width, theme.GOLD, .003,
                                  x=self.text_entity.x if align == 'center' else
                                  self.text_entity.x + self.text_entity.width / 2,
                                  y=-h * .3, z=-.003, enabled=False)
        if group is not None:
            group.add(self)
        self.refresh()

    @property
    def text(self):
        return self.text_entity.text

    @text.setter
    def text(self, value):
        self.text_entity.text = value.upper()

    def set_kind(self, kind):
        self.kind = kind
        self.refresh()

    def refresh(self):
        k = self.KINDS[self.kind]
        quiet = self.kind == 'quiet'
        if self._disabled:
            face, edge, rim, ink = (color.clear if quiet else theme.OFF_FACE), theme.EDGE, \
                (color.clear if quiet else theme.OFF_FACE), theme.OFF_TEXT
        else:
            face = k['press'] if self.pressed else (k['hover'] if (self.hovered_ or self.focused) else k['face'])
            edge, rim = k['edge'], k['rim']
            ink = theme.GOLD if quiet and (self.focused or self.hovered_) else k['ink']
        self.face.color = face
        self.edge.color = edge
        self.rim.color = rim
        self.text_entity.color = ink
        if self.icon_entity:
            self.icon_entity.color = ink
        if self.key_entity:
            self.key_entity.color = theme.OFF_TEXT if self._disabled else (
                color.rgba(34, 26, 14, 170) if self.kind == 'primary' else theme.MUTED)
        self.ring.enabled = self.focused and not quiet
        if self.marker:
            self.marker.enabled = self.focused
        if self.underline:
            self.underline.enabled = self.focused
        self.top.y = -theme.DEPTH * .75 if self.pressed else 0

    def press(self):
        if self._disabled or not self.enabled:
            return
        self.pressed = True
        self.refresh()
        invoke(self._release, delay=.09)
        if self.action:
            invoke(self.action, delay=.05)     # let the press show before the screen changes

    def _release(self):
        if self:
            self.pressed = False
            self.refresh()


def back_button(on_click, parent=camera.ui, x=0, y=0, w=.2, **kw):
    """Quiet 'BACK' with its Esc shortcut, for the top-left of sub screens."""
    return UIButton('Back', on_click, parent=parent, x=x, y=y, w=w, kind='quiet', key='Esc',
                    align='left', icon=lambda p, s, c, **k: icons.chevron(p, s * .9, c, 'left', **k), **kw)


def icon_button(icon, on_click, parent=camera.ui, x=0, y=0, size=theme.BUTTON_H, key=None, **kw):
    """Square plate with only an icon (HUD pause / restart). The key, if any, is captioned under it."""
    b = UIButton('', on_click, parent=parent, x=x, y=y, w=size, h=size, icon=icon, marker=None, **kw)
    if key:
        b.caption = label(b, key, theme.TINY, theme.MUTED, theme.FONT_LABEL, y=-size / 2 - theme.DEPTH - .016)
    return b


# ---------------------------------------------------------------- containers

class Panel(Entity):
    """A dark plate with a thin rim. title adds a heading and a divider; content_top is the y under it."""

    def __init__(self, w, h, parent=camera.ui, x=0, y=0, title=None, col=theme.PANEL, title_col=theme.TEXT, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.w, self.h = w, h
        plate(self, w + 2 * theme.RIM_W, h + 2 * theme.RIM_W, theme.PANEL_RIM, theme.CHAMFER * 1.4,
              shade=False, z=.006)
        self.fill = plate(self, w, h, col, theme.CHAMFER * 1.4, shade=False, z=.005)
        self.title = None
        self.content_top = h / 2 - theme.PAD
        if title:
            self.title = label(self, title.upper(), theme.SUBHEAD, title_col, theme.FONT_LABEL,
                               origin=(0, .5), y=h / 2 - theme.PAD * .9, max_width=w - 2 * theme.PAD, z=-.001)
            ty = self.title.y - self.title.height - .016
            line(self, w - 2 * theme.PAD, y=ty, z=-.001)
            self.content_top = ty - .02


class Modal(Entity):
    """A veil over everything and a panel in the middle. Modal.any_open() tells screens to keep quiet."""

    stack = []

    def __init__(self, w=.6, h=.42, title=None, parent=camera.ui, **kw):
        super().__init__(parent=parent, z=-.3, **kw)
        self.veil = Entity(parent=self, model='quad', scale=(8, 2), color=theme.DIM, z=.02, collider='box')
        self.panel = Panel(w, h, parent=self, title=title)
        self.panel.scale = .95
        self.panel.animate_scale(1, duration=theme.MEDIUM)
        Modal.stack.append(self)

    @classmethod
    def any_open(cls):
        cls.stack = [m for m in cls.stack if m]
        return bool(cls.stack)

    def close(self):
        if self in Modal.stack:
            Modal.stack.remove(self)
        destroy(self)


class ConfirmDialog(Modal):
    """Ask before doing something that cannot be undone. Esc cancels, Enter takes the focused button.

    danger=True starts with the focus on Cancel and colours the confirm button as a warning.
    """

    def __init__(self, title, message, on_confirm, on_cancel=None, confirm='Confirm', cancel='Cancel',
                 danger=False, w=.62, **kw):
        wrap = int((w - 2 * theme.PAD) * 62)          # characters per line at BODY size
        lines = max(1, -(-len(message) // wrap))
        h = .19 + .036 * lines + theme.BUTTON_H
        super().__init__(w=w, h=h, title=title, **kw)
        self.on_confirm, self.on_cancel = on_confirm, on_cancel
        p = self.panel
        label(p, message, theme.BODY, theme.MUTED, theme.FONT_BODY, origin=(0, .5), y=p.content_top,
              wordwrap=wrap, z=-.002)
        self.group = FocusGroup(horizontal=True)
        bw = (w - 3 * theme.PAD) / 2
        by = -h / 2 + theme.PAD + theme.BUTTON_H / 2 + theme.DEPTH
        self.cancel_button = UIButton(cancel, self._cancel, parent=p, x=-bw / 2 - theme.PAD / 2, y=by, w=bw,
                                      key='Esc', marker='below', group=self.group)
        self.confirm_button = UIButton(confirm, self._confirm, parent=p, x=bw / 2 + theme.PAD / 2, y=by, w=bw,
                                       kind='danger' if danger else 'primary', key='Enter', marker='below',
                                       group=self.group)
        self.group.focus(self.cancel_button if danger else self.confirm_button)

    def input(self, key):
        if key == 'escape':
            self._cancel()
        else:
            self.group.input(key)

    def _confirm(self):
        self.close()
        if self.on_confirm:
            self.on_confirm()

    def _cancel(self):
        self.close()
        if self.on_cancel:
            self.on_cancel()


# ---------------------------------------------------------------- pickers

class Stepper(Entity):
    """‹ value › picker. on_step(step) gets -1 or +1; set .value / .sub to change the text."""

    def __init__(self, value='', on_step=None, parent=camera.ui, x=0, y=0, w=.44, h=theme.BUTTON_H,
                 sub=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.on_step = on_step
        bw = h
        mk = lambda d: (lambda p, s, c, **k: icons.chevron(p, s, c, d, **k))
        self.prev = UIButton('', lambda: self._step(-1), parent=self, x=-w / 2 + bw / 2, w=bw, h=h,
                             icon=mk('left'), marker=None)
        self.next = UIButton('', lambda: self._step(1), parent=self, x=w / 2 - bw / 2, w=bw, h=h,
                             icon=mk('right'), marker=None)
        self.room = w - 2 * bw - .02
        self.value_text = label(self, '', theme.SUBHEAD * 1.1, theme.TEXT, theme.FONT_TITLE,
                                y=.01 if sub is not None else 0)
        self.sub_text = label(self, '', theme.TINY, theme.MUTED, theme.FONT_LABEL, y=-.026)
        self.value, self.sub = value, sub or ''

    def _step(self, step):
        if self.on_step:
            self.on_step(step)

    @property
    def value(self):
        return self.value_text.text

    @value.setter
    def value(self, text):
        self.value_text.scale = theme.SUBHEAD * 1.1
        self.value_text.text = text
        fit(self.value_text, self.room)

    @property
    def sub(self):
        return self.sub_text.text

    @sub.setter
    def sub(self, text):
        self.sub_text.scale = theme.TINY
        self.sub_text.text = text.upper()
        fit(self.sub_text, self.room)


class Tabs(Entity):
    """Segmented control: the chosen segment is gold. options: [(label, value)]; on_change(value)."""

    def __init__(self, options, value=None, on_change=None, parent=camera.ui, x=0, y=0, w=.44,
                 h=theme.BUTTON_H * .82, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.options = list(options)
        self.on_change = on_change
        seg = w / len(self.options)
        self.buttons = [UIButton(text, (lambda v=val: self.select(v, notify=True)), parent=self,
                                 x=-w / 2 + seg * (i + .5), w=seg - .008, h=h, size=theme.SMALL * 1.1, marker=None)
                        for i, (text, val) in enumerate(self.options)]
        self.value = None
        self.select(value if value is not None else self.options[0][1])

    def select(self, value, notify=False):
        self.value = value
        for b, (_, val) in zip(self.buttons, self.options):
            b.set_kind('primary' if val == value else 'secondary')
        if notify and self.on_change:
            self.on_change(value)

    def step(self, step):
        values = [v for _, v in self.options]
        self.select(values[(values.index(self.value) + step) % len(values)], notify=True)


class LevelTile(_Focusable):
    """A level's number on a square plate.

    state: 'done' (green, check), 'open' (charcoal), 'locked' (dim, padlock, cannot be picked).
    selected: the level currently chosen (gold rim and number). Focus adds the pointer below.
    """

    def __init__(self, number, on_pick=None, state='open', selected=False, parent=camera.ui, x=0, y=0,
                 size=.1, caption=True, group=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.number, self.on_pick, self.size = number, on_pick, size
        self.state, self.selected = state, selected
        s = size
        self.sel_ring = plate(self, s + 2 * theme.FOCUS_W, s + 2 * theme.FOCUS_W, theme.GOLD_RIM, shade=False,
                              z=.004)
        self.rim = plate(self, s + 2 * theme.RIM_W, s + 2 * theme.RIM_W, theme.RIM, shade=False, z=.003)
        self.face = plate(self, s, s, theme.FACE, z=.002, collider='box')
        self._hook(self.face)
        self.num = label(self, '{:02d}'.format(number), theme.HEADING * s / .1, theme.TEXT, theme.FONT_TITLE,
                         y=s * .1, max_width=s * .86, z=-.002)
        self.badge = None
        self.caption = label(self, '', theme.TINY, theme.MUTED, theme.FONT_LABEL,
                             y=-s / 2 - .022, z=-.002) if caption else None
        self.marker = icons.triangle(self, .014, theme.GOLD, -90, y=-s / 2 - (.046 if caption else .02),
                                     z=-.003, enabled=False)
        self._disabled = state == 'locked'
        if group is not None:
            group.add(self)
        self.refresh()

    def set(self, state=None, selected=None):
        if state is not None:
            self.state = state
            self._disabled = state == 'locked'
        if selected is not None:
            self.selected = selected
        self.refresh()

    def refresh(self):
        s = self.size
        st = self.state
        face = {'done': theme.DONE_FACE, 'locked': color.rgb(28, 31, 37)}.get(st, theme.FACE)
        if (self.hovered_ or self.focused) and st != 'locked':
            face = face.tint(.08)
        self.face.color = face
        self.rim.color = {'done': theme.DONE_RIM, 'locked': color.rgb(48, 52, 60)}.get(st, theme.RIM)
        self.sel_ring.enabled = self.selected or self.focused
        self.sel_ring.color = theme.GOLD_RIM if self.selected else theme.MUTED
        self.num.color = theme.GOLD if self.selected else (theme.OFF_TEXT if st == 'locked' else theme.TEXT)
        badge = st in ('done', 'locked')
        self.num.scale = theme.HEADING * s / .1 * (.78 if badge else 1)
        fit(self.num, s * .86)
        self.num.y = s * (.14 if badge else .02)
        if self.badge:
            destroy(self.badge)
            self.badge = None
        if st == 'done':
            self.badge = icons.check(self, s * .32, theme.GREEN, y=-s * .24, z=-.002)
        elif st == 'locked':
            self.badge = icons.lock(self, s * .3, theme.OFF_TEXT, y=-s * .24, z=-.002)
        if self.caption:
            text = 'selected' if self.selected else {'done': 'completed', 'locked': 'locked'}.get(st, 'available')
            self.caption.text = text.upper()
            self.caption.color = theme.GOLD if self.selected else theme.MUTED
        self.marker.enabled = self.focused

    def press(self):
        if self._disabled:
            return
        if self.on_pick:
            self.on_pick(self.number)


# ---------------------------------------------------------------- settings controls

class Slider(_Focusable):
    """LABEL  [====o-----]  70%   value 0..1, on_change(value). Drag it, click it, or ←/→ when focused."""

    def __init__(self, text, value=.5, on_change=None, parent=camera.ui, x=0, y=0, w=.56, h=theme.BUTTON_H,
                 step=.05, group=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.on_change, self.step_size = on_change, step
        self.value = None
        self.dragging = False
        self.ring = plate(self, w + 2 * theme.FOCUS_W, h + 2 * theme.FOCUS_W, theme.GOLD_RIM, shade=False, z=.004)
        self.bed = plate(self, w, h, theme.FACE, z=.003, collider='box')
        self.bed.on_mouse_enter = self._enter
        self.bed.on_mouse_exit = self._exit
        lw = w * .3
        self.name_text = label(self, text.upper(), theme.LABEL, theme.TEXT, theme.FONT_LABEL, origin=(-.5, 0),
                          x=-w / 2 + theme.PAD, max_width=lw - theme.PAD, z=-.002)
        self.x0 = -w / 2 + lw
        self.x1 = w / 2 - .09
        tw = self.x1 - self.x0
        self.track = plate(self, tw, .012, theme.EDGE, .003, shade=False, x=(self.x0 + self.x1) / 2, z=-.001,
                           collider='box')
        self.track.on_click = self._grab
        self.track.on_mouse_enter = self._enter
        self.track.on_mouse_exit = self._exit
        self.fill = Entity(parent=self, model='quad', origin=(-.5, 0), x=self.x0, scale=(tw, .012),
                           color=theme.GOLD, z=-.002)
        self.knob = plate(self, .018, .036, theme.GOLD, .004, z=-.004, collider='box')
        self.knob.on_click = self._grab
        self.amount = label(self, '', theme.SMALL, theme.MUTED, theme.FONT_LABEL, origin=(.5, 0),
                            x=w / 2 - theme.PAD * .6, z=-.002)
        if group is not None:
            group.add(self)
        self.set(value)
        self.refresh()

    def set(self, value, notify=False):
        value = max(0.0, min(1.0, round(value / self.step_size) * self.step_size))
        changed = value != self.value
        self.value = value
        tw = self.x1 - self.x0
        self.fill.scale_x = max(.0001, tw * value)
        self.knob.x = self.x0 + tw * value
        self.amount.text = '{}%'.format(int(round(value * 100)))
        if notify and changed and self.on_change:
            self.on_change(value)

    def refresh(self):
        self.ring.enabled = self.focused
        self.bed.color = theme.FACE_HOVER if (self.focused or self.hovered_) else theme.FACE
        self.name_text.color = theme.GOLD if self.focused else theme.TEXT

    def take_key(self, key):
        if key in ('left arrow', 'right arrow'):
            self.set(self.value + self.step_size * (1 if key == 'right arrow' else -1), notify=True)
            return True
        return False

    def press(self):
        pass

    def _grab(self):
        if self.group:
            self.group.focus(self)
        self.dragging = True
        self._follow()

    def _follow(self):
        local_x = self.getRelativePoint(camera.ui, Vec3(mouse.x, mouse.y, 0)).x
        self.set((local_x - self.x0) / (self.x1 - self.x0), notify=True)

    def update(self):
        if self.dragging:
            if mouse.left:
                self._follow()
            else:
                self.dragging = False


class Checkbox(_Focusable):
    """LABEL  [✓] ON. on_change(bool)."""

    def __init__(self, text, value=False, on_change=None, parent=camera.ui, x=0, y=0, w=.56,
                 h=theme.BUTTON_H, group=None, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.on_change = on_change
        self.value = None
        self.ring = plate(self, w + 2 * theme.FOCUS_W, h + 2 * theme.FOCUS_W, theme.GOLD_RIM, shade=False, z=.004)
        self.bed = plate(self, w, h, theme.FACE, z=.003, collider='box')
        self._hook(self.bed)
        self.name_text = label(self, text.upper(), theme.LABEL, theme.TEXT, theme.FONT_LABEL, origin=(-.5, 0),
                          x=-w / 2 + theme.PAD, max_width=w * .62, z=-.002)
        bx = w / 2 - .12
        self.box_rim = plate(self, .036, .036, theme.GOLD, .004, shade=False, x=bx, z=-.001)
        self.box = plate(self, .029, .029, theme.EDGE, .003, shade=False, x=bx, z=-.002)
        self.tick = icons.check(self, .026, theme.GOLD, x=bx, z=-.003)
        self.state_text = label(self, '', theme.SMALL, theme.MUTED, theme.FONT_LABEL, origin=(-.5, 0),
                                x=bx + .032, z=-.002)
        if group is not None:
            group.add(self)
        self.set(value)
        self.refresh()

    def set(self, value, notify=False):
        self.value = bool(value)
        self.tick.enabled = self.value
        self.box_rim.color = theme.GOLD if self.value else theme.RIM
        self.state_text.text = 'ON' if self.value else 'OFF'
        if notify and self.on_change:
            self.on_change(self.value)

    def refresh(self):
        self.ring.enabled = self.focused
        self.bed.color = theme.FACE_HOVER if (self.focused or self.hovered_) else theme.FACE
        self.name_text.color = theme.GOLD if self.focused else theme.TEXT

    def press(self):
        if self.group:
            self.group.focus(self)
        self.set(not self.value, notify=True)


class ProgressBar(Entity):
    """Loading bar: caption above, gold fill, percentage on the right. set(fraction, caption=None)."""

    def __init__(self, caption='Loading', parent=camera.ui, x=0, y=0, w=.5, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.w = w
        self.caption = label(self, caption.upper(), theme.SMALL, theme.TEXT, theme.FONT_LABEL, origin=(-.5, 0),
                             x=-w / 2, y=.026, max_width=w * .8)
        self.amount = label(self, '0%', theme.SMALL, theme.GOLD, theme.FONT_LABEL, origin=(.5, 0), x=w / 2, y=.026)
        plate(self, w + .006, .018, theme.RIM, .004, shade=False, z=.002)
        plate(self, w, .012, theme.EDGE, .003, shade=False, z=.001)
        self.fill = Entity(parent=self, model='quad', origin=(-.5, 0), x=-w / 2, scale=(.0001, .012),
                           color=theme.GOLD)
        self.value = 0.0

    def set(self, fraction, caption=None):
        self.value = max(0.0, min(1.0, fraction))
        self.fill.scale_x = max(.0001, self.w * self.value)
        self.amount.text = '{}%'.format(int(self.value * 100))
        if caption is not None:
            self.caption.text = caption.upper()
            fit(self.caption, self.w * .8)


# ---------------------------------------------------------------- read-outs

class StatCard(Entity):
    """One big number with a small caption under it (Algorithms results)."""

    def __init__(self, caption, value='—', parent=camera.ui, x=0, y=0, w=.2, h=.11, accent=theme.GOLD, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.w = w
        plate(self, w + 2 * theme.RIM_W, h + 2 * theme.RIM_W, theme.PANEL_RIM, shade=False, z=.002)
        plate(self, w, h, theme.FACE_PRESS, z=.001)
        self.value_text = label(self, '', theme.STAT, accent, theme.FONT_TITLE, y=h * .12, z=-.002)
        self.caption_text = label(self, caption.upper(), theme.TINY, theme.MUTED, theme.FONT_LABEL,
                                  y=-h * .3, max_width=w - .02, z=-.002)
        self.value = value

    @property
    def value(self):
        return self.value_text.text

    @value.setter
    def value(self, text):
        self.value_text.scale = theme.STAT
        self.value_text.text = text
        fit(self.value_text, self.w - .02)


class HUDBar(Entity):
    """Compact strip for the top-left corner: [cube] NAME | FLOOR 01 / 10 | MOVES 08.

    set(name, stats) where stats is [(caption, value, suffix)]; it resizes to its content.
    """

    H = .056

    def __init__(self, parent=camera.ui, x=0, y=0, **kw):
        super().__init__(parent=parent, x=x, y=y, **kw)
        self.parts = Entity(parent=self)
        self.bed = None

    def set(self, name, stats=()):
        destroy(self.parts)
        if self.bed:
            destroy(self.bed)
        self.parts = Entity(parent=self)
        h, pad = self.H, .022
        x = pad
        icons.cube(self.parts, h * .55, theme.MUTED, x=x + h * .27, z=-.002)
        x += h * .55 + .014
        t = label(self.parts, name.upper(), theme.LABEL, theme.TEXT, theme.FONT_LABEL, origin=(-.5, 0), x=x,
                  max_width=.3, z=-.002)
        x += t.width + pad
        for caption, value, suffix in stats:
            line(self.parts, .0018, theme.DIVIDER, h * .6, x=x, z=-.002)
            x += pad
            c = label(self.parts, caption.upper(), theme.SMALL, theme.MUTED, theme.FONT_LABEL, origin=(-.5, 0),
                      x=x, z=-.002)
            x += c.width + .01
            v = label(self.parts, str(value), theme.SUBHEAD * 1.25, theme.GOLD, theme.FONT_TITLE, origin=(-.5, 0),
                      x=x, y=.002, z=-.002)
            x += v.width
            if suffix:
                s = label(self.parts, suffix, theme.SMALL, theme.MUTED, theme.FONT_LABEL, origin=(-.5, 0),
                          x=x + .008, z=-.002)
                x += .008 + s.width
            x += pad
        self.width = x
        self.bed = Entity(parent=self)
        plate(self.bed, x + 2 * theme.RIM_W, h + 2 * theme.RIM_W, theme.PANEL_RIM, shade=False, x=x / 2, z=.002)
        plate(self.bed, x, h, theme.PANEL, shade=False, x=x / 2, z=.001)


class KeyHint(Entity):
    """A row of key chips and what they do, centred at y, e.g. [('arrows', 'move'), ('R', 'restart')].

    'arrows' draws all four arrow keys, 'updown' and 'leftright' just the pair.
    """

    CHIP = .032

    def __init__(self, items, parent=camera.ui, y=-.462, **kw):
        super().__init__(parent=parent, y=y, **kw)
        self.set(items)

    def _chip(self, group, x, w, h):
        plate(group, w + .004, h + .004, theme.RIM, .004, shade=False, x=x + w / 2, z=.002)
        plate(group, w, h, theme.FACE_PRESS, .004, x=x + w / 2, z=.001)

    def set(self, items):
        for child in list(self.children):
            destroy(child)
        h = self.CHIP
        cursor, parts = 0.0, []
        for keys, action in items:
            group = Entity(parent=self)
            x = 0.0
            groups = {'arrows': ('left', 'up', 'down', 'right'), 'updown': ('up', 'down'),
                      'leftright': ('left', 'right')}
            for key in groups.get(keys, (keys,)):
                if key in icons.ARROW_ANGLES:
                    w = h
                    self._chip(group, x, w, h)
                    icons.arrow(group, h * .36, theme.TEXT, key, x=x + w / 2, z=-.001)
                else:
                    t = label(group, key.upper(), theme.TINY, theme.TEXT, theme.FONT_LABEL, z=-.001)
                    w = max(h, t.width + .018)
                    t.x = x + w / 2
                    self._chip(group, x, w, h)
                x += w + .005
            t = label(group, action, theme.SMALL, theme.MUTED, theme.FONT_BODY, origin=(-.5, 0), x=x + .006)
            x += .006 + t.width
            group.x = cursor
            parts.append(group)
            cursor += x + .04
        total = cursor - .04
        for g in parts:
            g.x -= total / 2


class Toast(Entity):
    """A short message that fades out by itself. Several stack downwards instead of overlapping."""

    live = []
    TOP = .38
    H = .052

    def __init__(self, text, parent=camera.ui, duration=2.4, col=theme.TEXT, **kw):
        super().__init__(parent=parent, z=-.4, **kw)
        t = label(self, text, theme.BODY, col, theme.FONT_LABEL, max_width=1.0, z=-.002)
        w = t.width + .06
        plate(self, w + 2 * theme.RIM_W, self.H + 2 * theme.RIM_W, theme.PANEL_RIM, shade=False, z=.002)
        plate(self, w, self.H, theme.PANEL, shade=False, z=.001)
        Toast.live = [x for x in Toast.live if x]
        Toast.live.append(self)
        self._reflow()
        invoke(self._fade, delay=duration)

    @classmethod
    def _reflow(cls):
        cls.live = [x for x in cls.live if x]
        for i, toast in enumerate(cls.live):
            toast.y = cls.TOP - i * (cls.H + .012)

    def _fade(self):
        if not self:
            return
        for e in self.children:
            e.animate_color(color.clear, duration=.25)
        invoke(self._gone, delay=.28)

    def _gone(self):
        if self in Toast.live:
            Toast.live.remove(self)
        destroy(self)
        Toast._reflow()
