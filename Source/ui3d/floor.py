"""One storey of the tower in 3D: the slab, the path tiles, walls, furniture or rooftop equipment.

The path keeps the playfield's cells, raised a little, lighter and bevelled so it reads at a glance;
the floor around it is darker and only lightly furnished (a few groups, plenty of empty floor).
All lit geometry uses models/prim/*.glb (Ursina's own cube has no normals); textures come from SDXL
(tools/comfy_gen.py) with plain colours as the fallback.
"""
import math
import random

from ursina import Cone, Entity, Vec3, color, destroy

from .world import ASSETS, FURNITURE, floor_y

MX, MY = 3, 2
TILE_TOP = 0.12
BOX, BALL, CYL = 'models/prim/box', 'models/prim/ball', 'models/prim/cyl'


def tex(name, fallback=None):
    return 'textures/' + name if (ASSETS / 'textures' / (name + '.png')).exists() else fallback


def prop(parent, name, pos, angle=0, scale=FURNITURE):
    """A Kenney model centred on ``pos`` (x/z) and standing on its y, turned by ``angle`` degrees."""
    holder = Entity(parent=parent, position=pos, rotation_y=angle)
    m = Entity(parent=holder, model='models/' + name, scale=scale)
    for mat in m.findAllMaterials():            # Kenney nature models are marked fully metallic, which renders
        mat.setMetallic(0)                      # black without an environment map
    b = m.model_bounds
    m.position = Vec3(-b.center.x * scale, -b.start.y * scale, -b.center.z * scale)
    return holder


def box(parent, pos, size, col=color.white, texture=None, **kw):
    return Entity(parent=parent, model=BOX, position=pos, scale=size, color=col, texture=texture, **kw)


def glow(parent, pos, size, col, model=BOX, **kw):
    """Unlit (self-lit) piece: lamps, beacons, guide arrows."""
    e = Entity(parent=parent, model=model, position=pos, scale=size, color=col, **kw)
    e.setLightOff()
    return e


class Floor:
    def __init__(self, session, index, count):
        self.session, self.index, self.count = session, index, count
        self.base = floor_y(index)
        self.roof = index == count - 1                       # the climb ends on the rooftop
        self.root = Entity()
        self.rng = random.Random(1000 + session.level.level)
        kinds = session.level.kinds
        xs, ys = [x for x, _ in kinds], [y for _, y in kinds]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        self.fp = (min(xs) - MX, min(ys) - MY, max(xs) + MX, max(ys) + MY)
        self.tiles = Entity(parent=self.root)
        self.beacon, self.arrow = None, None
        self._slab()
        if self.roof:
            self._roof()
        else:
            self._room()
            self._furnish()
        self.refresh()
        lv = session.level                                      # elevators: one to leave, one we arrived in
        self.lift = None if self.roof else Lift(self.root, self.at(*lv.end), self._door_yaw(lv.end), True)
        self.arrival = Lift(self.root, self.at(*lv.start), self._door_yaw(lv.start), False) if index > 0 else None

    def _door_yaw(self, cell):
        """Doors face a neighbouring path cell (preferring the camera's side), so the block walks straight in."""
        from .character import yaw_for
        kinds = self.session.level.kinds
        for dx, dy in ((0, 1), (1, 0), (-1, 0), (0, -1)):        # engine y grows towards the camera
            if (cell[0] + dx, cell[1] + dy) in kinds:
                return yaw_for(dx, -dy)
        return yaw_for(0, -1)

    # ---- geometry helpers ----
    def at(self, x, y, h=0.0):
        return Vec3(x, self.base + h, -y)

    @property
    def centre(self):
        bx0, by0, bx1, by1 = self.bbox
        return self.at((bx0 + bx1) / 2, (by0 + by1) / 2)

    @property
    def span(self):
        bx0, by0, bx1, by1 = self.bbox
        return max(bx1 - bx0 + 1, (by1 - by0 + 1) * 1.25)

    # ---- static parts ----
    def _slab(self):
        fx0, fy0, fx1, fy1 = self.fp
        w, d = fx1 - fx0 + 1, fy1 - fy0 + 1
        c = self.at((fx0 + fx1) / 2, (fy0 + fy1) / 2, -0.15)
        if self.roof:
            box(self.root, c, (w, 0.3, d), color.rgb(215, 215, 225), tex('roof', 'textures/gravel'), texture_scale=(w / 2, d / 2))
        else:
            box(self.root, c, (w, 0.3, d), color.rgb(150, 132, 112), tex('oak', 'textures/wood'), texture_scale=(w / 2, d / 2))
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.5, -3.2), (w, 6.2, 0.4), color.rgb(70, 72, 82))

    def _room(self):
        """Back and side walls with windows; the near (south) side is cut away, with a low glass rail."""
        fx0, fy0, fx1, fy1 = self.fp
        for x in range(fx0, fx1 + 1):                          # back wall
            prop(self.root, 'wallWindow' if (x - fx0) % 3 == 1 else 'wall', self.at(x, fy0 - 0.5), 0, 1.0)
        for y in range(fy0, fy1 + 1):                          # side walls
            for x, angle in ((fx0 - 0.5, 90), (fx1 + 0.5, -90)):
                prop(self.root, 'wallWindow' if (y - fy0) % 3 == 1 else 'wall', self.at(x, y), angle, 1.0)
        w = fx1 - fx0 + 1
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.48, 0.25), (w, 0.5, 0.04), color.rgba(170, 210, 235, 90))
        for x in range(fx0, fx1 + 2, 2):
            box(self.root, self.at(x - 0.5, fy1 + 0.48, 0.25), (0.06, 0.5, 0.06), color.rgb(120, 130, 140))
        for x in range(fx0 + 2, fx1, 4):                       # warm ceiling-lamp pools on the floor
            for y in range(fy0 + 1, fy1, 4):
                glow(self.root, self.at(x, y, 0.005), (2.2, 0.005, 2.2), color.rgba(255, 220, 160, 26), model='circle',
                     rotation_x=90)

    def _roof(self):
        fx0, fy0, fx1, fy1 = self.fp
        w, d = fx1 - fx0 + 1, fy1 - fy0 + 1
        par = color.rgb(150, 150, 160)                         # parapet
        conc = tex('concrete', None)
        box(self.root, self.at((fx0 + fx1) / 2, fy0 - 0.6, 0.35), (w + 1.4, 0.7, 0.4), par, conc)
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.6, 0.2), (w + 1.4, 0.4, 0.4), par, conc)
        for x in (fx0 - 0.6, fx1 + 0.6):
            box(self.root, self.at(x, (fy0 + fy1) / 2, 0.35), (0.4, 0.7, d + 1.2), par, conc)
        walk = set(self.session.level.kinds)
        free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
        near = {c for c in free if any((c[0] + dx, c[1] + dy) in walk for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
        rng = self.rng
        far = sorted(free - near)
        if far:                                                # antenna with a blinking light
            ax, ay = rng.choice(far)
            free.discard((ax, ay))
            Entity(parent=self.root, model=CYL, position=self.at(ax, ay, 1.6), scale=(0.08, 3.2, 0.08),
                   color=color.rgb(90, 90, 96))
            self.beacon = glow(self.root, self.at(ax, ay, 3.25), 0.16, color.rgb(255, 60, 50), model=BALL)
        placed = 0
        for x, y in sorted(free, key=lambda c: (c in near, rng.random())):   # mostly away from the path
            if (x, y) not in free or placed >= 9 or rng.random() > (0.08 if (x, y) in near else 0.22):
                continue
            kind = rng.choice(['ac', 'ac', 'tank', 'crate', 'vent'])
            if kind in ('tank', 'ac') and not {(x + 1, y), (x, y + 1), (x + 1, y + 1)} <= free:
                kind = rng.choice(['vent', 'crate'])
            placed += 1
            if kind == 'ac':                                   # condenser: louvred box, fan panel on top
                for c in ((x, y), (x + 1, y)):
                    free.discard(c)
                p = self.at(x + 0.5, y, 0.45)
                box(self.root, p, (1.6, 0.9, 0.9), color.rgb(205, 207, 212), tex('ac_side'))
                box(self.root, p + Vec3(0, 0.46, 0), (1.55, 0.03, 0.86), color.white, tex('ac_top'))
            elif kind == 'tank':
                for c in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                    free.discard(c)
                p = self.at(x + 0.5, y + 0.5, 0.9)
                Entity(parent=self.root, model=CYL, position=p, scale=(1.6, 1.8, 1.6), color=color.rgb(190, 192, 198),
                       texture=tex('corrugated'))
                Entity(parent=self.root, model=CYL, position=p + Vec3(0, 0.92, 0), scale=(1.66, 0.06, 1.66),
                       color=color.white, texture=tex('tank_top'))
            elif kind == 'vent':
                free.discard((x, y))
                Entity(parent=self.root, model=CYL, position=self.at(x, y, 0.2), scale=(0.4, 0.4, 0.4),
                       color=color.rgb(150, 152, 160), texture=tex('corrugated'))
                Entity(parent=self.root, model=BALL, position=self.at(x, y, 0.42), scale=(0.5, 0.18, 0.5),
                       color=color.rgb(120, 122, 130))
            else:
                free.discard((x, y))
                box(self.root, self.at(x, y, 0.35), (0.7, 0.7, 0.7), color.white, tex('crate'))

    def _furnish(self):
        fx0, fy0, fx1, fy1 = self.fp
        bx0, by0, bx1, by1 = self.bbox
        walk = set(self.session.level.kinds)
        free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
        used, rng = set(), self.rng

        def room_for(cells, gap=1):
            return cells <= free and not any((x + dx, y + dy) in used for x, y in cells
                                             for dx in range(-gap, gap + 1) for dy in range(-gap, gap + 1))

        def take(cells):
            used.update(cells)
            free.difference_update(cells)

        def desk(x, y, angle):
            take({(x, y)})
            g = Entity(parent=self.root, position=self.at(x, y), rotation_y=angle)
            prop(g, 'desk', Vec3(0, 0, 0.1))
            prop(g, 'computerScreen', Vec3(0, 0.48, 0.22))
            prop(g, 'chairDesk', Vec3(0, 0, -0.42), 180)

        groups = 0
        inside = sorted((c for c in free if bx0 <= c[0] <= bx1 and by0 <= c[1] <= by1), key=lambda c: rng.random())
        for x, y in inside:                                      # at most a few groups in the playfield's gaps
            if groups >= 3:
                break
            block = {(x + i, y + j) for i in range(2) for j in range(2)}
            if groups == 0 and room_for(block):
                take(block)
                c = self.at(x + 0.5, y + 0.5)
                prop(self.root, 'rugRectangle', c + Vec3(0, 0.01, 0), 0, 1.5)
                prop(self.root, 'tableRound', c, 0, 1.6)
                for a in range(4):
                    ang = a * 90 + 45
                    off = Vec3(math.sin(math.radians(ang)), 0, math.cos(math.radians(ang))) * 0.95
                    prop(self.root, 'chair', c + off, ang + 180)
                groups += 1
            elif room_for({(x, y), (x, y + 1)}, gap=2):
                desk(x, y, 0)
                desk(x, y + 1, 180)
                groups += 1
            elif room_for({(x, y)}, gap=2) and rng.random() < 0.5:
                take({(x, y)})
                prop(self.root, 'pottedPlant', self.at(x, y))
                groups += 1
        for x in range(fx0 + 1, fx1, 4):                         # back wall: a little storage
            if room_for({(x, fy0)}) and rng.random() < 0.6:
                take({(x, fy0)})
                prop(self.root, rng.choice(['bookcaseOpen', 'bookcaseClosedDoors']), self.at(x, fy0 - 0.15), 180)
        for corner in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
            if room_for({corner}):
                take({corner})
                prop(self.root, rng.choice(['pottedPlant', 'lampRoundFloor']), self.at(*corner))

    # ---- the playfield, rebuilt whenever bridges change ----
    def refresh(self):
        for e in list(self.tiles.children):
            destroy(e)
        s = self.session
        office = not self.roof
        path_tex = tex('carpet' if office else 'paver', 'textures/concrete')
        path_col = color.rgb(220, 226, 240) if office else color.rgb(235, 232, 225)
        self.arrow = None
        for (x, y) in s.level.kinds:
            kind = s.tile_at(x, y)
            p = self.at(x, y, TILE_TOP / 2)
            if kind == 'bridge_closed':                          # striped barrier across the gap
                box(self.tiles, self.at(x, y, 0.28), (0.9, 0.12, 0.12), color.rgb(250, 200, 40))
                for dx in (-0.42, 0.42):
                    Entity(parent=self.tiles, model=CYL, position=self.at(x + dx, y, 0.2), scale=(0.07, 0.4, 0.07),
                           color=color.rgb(60, 60, 66))
                continue
            top = self.at(x, y, TILE_TOP + 0.005)
            if kind == 'goal' and self.roof:                     # end of the climb: a lit helipad
                box(self.tiles, p, (0.96, TILE_TOP, 0.96), color.rgb(60, 64, 76))
                glow(self.tiles, top, (0.86, 0.01, 0.86), color.rgb(255, 205, 90), model='circle', rotation_x=90)
                for dx in (-0.17, 0.17):
                    glow(self.tiles, top + Vec3(dx, 0.01, 0), (0.07, 0.01, 0.42), color.rgb(40, 40, 48))
                glow(self.tiles, top + Vec3(0, 0.01, 0), (0.34, 0.01, 0.07), color.rgb(40, 40, 48))
                self.arrow = glow(self.tiles, self.at(x, y, 1.6), (0.36, 0.45, 0.36), color.rgb(255, 205, 90),
                                  model=Cone(4), rotation_x=180)
                continue
            t, c = path_tex, path_col
            if kind == 'fragile':
                t, c = tex('fragile', path_tex), color.rgb(255, 200, 170)
            elif kind == 'bridge_open':
                t, c = tex('steel', path_tex), color.white
            box(self.tiles, p, (0.96, TILE_TOP, 0.96), c, t)
            if kind == 'soft':
                Entity(parent=self.tiles, model=CYL, position=top, scale=(0.5, 0.03, 0.5), color=color.rgb(70, 130, 220))
            elif kind == 'heavy':
                for a in (45, -45):
                    box(self.tiles, top, (0.7, 0.03, 0.12), color.rgb(50, 50, 58), rotation_y=a)
            elif kind == 'split':
                for dx in (-0.22, 0.22):
                    box(self.tiles, top + Vec3(dx, 0, 0), (0.08, 0.03, 0.55), color.rgb(150, 80, 200))

    def animate(self, t):
        """Per frame: bob and spin the goal arrow, blink the elevator's up arrow."""
        if self.lift:
            self.lift.arrow.color = color.rgb(255, 205, 90) if int(t * 2) % 2 else color.rgb(120, 90, 40)
        if self.arrow:
            self.arrow.y = self.base + 1.55 + 0.12 * math.sin(t * 3)
            self.arrow.rotation_y = t * 90

    def destroy(self):
        destroy(self.root)


class Lift:
    """An elevator car standing on one cell: walls on three sides, two sliding doors on the side facing
    ``yaw`` (local -z) and a header with an up arrow. ``set_open(0..1)`` slides the doors."""
    H = 2.3

    def __init__(self, parent, pos, yaw, opened):
        self.root = Entity(parent=parent, position=pos, rotation_y=yaw)
        steel, dark = color.rgb(170, 176, 188), color.rgb(58, 60, 70)
        H, t = self.H, 0.06
        box(self.root, Vec3(0, TILE_TOP / 2, 0), (0.98, TILE_TOP, 0.98), color.rgb(110, 112, 122), tex('steel'))
        box(self.root, Vec3(0, H / 2, 0.47), (0.98, H, t), steel, tex('steel'))          # back wall
        for sx in (-0.47, 0.47):                                                          # side walls
            box(self.root, Vec3(sx, H / 2, 0), (t, H, 0.98), steel, tex('steel'))
        for sx in (-0.5, 0.5):                                                            # door frame
            box(self.root, Vec3(sx, H / 2, -0.5), (0.08, H, 0.08), dark)
        box(self.root, Vec3(0, H + 0.13, -0.47), (1.06, 0.26, 0.12), dark)               # header
        self.arrow = glow(self.root, Vec3(0, H + 0.13, -0.55), (0.14, 0.16, 0.02), color.rgb(255, 205, 90),
                          model=Cone(3))
        glow(self.root, Vec3(0, H - 0.05, 0), (0.6, 0.02, 0.6), color.rgb(255, 236, 200))  # ceiling light
        self.doors = [box(self.root, Vec3(0, H / 2, -0.53), (0.47, H - 0.06, 0.04), color.rgb(200, 205, 214),
                          tex('steel')) for _ in range(2)]
        self.set_open(1.0 if opened else 0.0)

    def set_open(self, k):
        for i, d in enumerate(self.doors):
            side = -1 if i == 0 else 1
            d.x = side * (0.24 + 0.47 * k)
