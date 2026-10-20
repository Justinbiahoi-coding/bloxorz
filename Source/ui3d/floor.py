"""One storey of the tower in 3D: the slab, the path tiles, walls, furniture or rooftop equipment.

The path keeps the playfield's cells; everything else is a real room (or the roof) around it.
Furniture follows the 2D layout rules: storage on the back wall, desks facing the side walls,
desk pairs and one meeting table in the gaps of the playfield, plenty of empty floor.
"""
import math
import random

from ursina import Entity, Vec3, color, destroy

from .world import FURNITURE, floor_y

MX, MY = 3, 2
TILE_TOP = 0.08


def prop(parent, name, pos, angle=0, scale=FURNITURE):
    """A Kenney model centred on ``pos`` (x/z) and standing on its y, turned by ``angle`` degrees."""
    holder = Entity(parent=parent, position=pos, rotation_y=angle)
    m = Entity(parent=holder, model='models/' + name, scale=scale)
    for mat in m.findAllMaterials():            # Kenney nature models are marked fully metallic, which renders
        mat.setMetallic(0)                      # black without an environment map
    b = m.model_bounds
    m.position = Vec3(-b.center.x * scale, -b.start.y * scale, -b.center.z * scale)
    return holder


def box(parent, pos, size, col, **kw):
    return Entity(parent=parent, model='cube', position=pos, scale=size, color=col, **kw)


class Floor:
    def __init__(self, session, index, count):
        self.session, self.index, self.count = session, index, count
        self.base = floor_y(index)
        self.roof = index == 0
        self.root = Entity()
        self.rng = random.Random(1000 + session.level.level)
        kinds = session.level.kinds
        xs, ys = [x for x, _ in kinds], [y for _, y in kinds]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))
        self.fp = (min(xs) - MX, min(ys) - MY, max(xs) + MX, max(ys) + MY)
        self.tiles = Entity(parent=self.root)
        self.beacon = None
        self._slab()
        if self.roof:
            self._roof()
        else:
            self._room()
            self._furnish()
        self.refresh()

    # ---- geometry helpers ----
    def at(self, x, y, h=0.0):
        return Vec3(x, self.base + h, -y)

    @property
    def centre(self):
        bx0, by0, bx1, by1 = self.bbox
        return self.at((bx0 + bx1) / 2, (by0 + by1) / 2)

    @property
    def size(self):
        fx0, fy0, fx1, fy1 = self.fp
        return max(fx1 - fx0 + 1, (fy1 - fy0 + 1) * 1.3)

    # ---- static parts ----
    def _slab(self):
        fx0, fy0, fx1, fy1 = self.fp
        w, d = fx1 - fx0 + 1, fy1 - fy0 + 1
        c = self.at((fx0 + fx1) / 2, (fy0 + fy1) / 2, -0.15)
        tex = 'textures/gravel' if self.roof else 'textures/wood'
        Entity(parent=self.root, model='cube', position=c, scale=(w, 0.3, d), texture=tex,
               texture_scale=(w / 3, d / 3), color=color.rgb(150, 146, 140) if self.roof else color.rgb(200, 185, 170))
        # the slab's front edge and the building below it, seen through the cut-away
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.5, -3.2), (w, 6.2, 0.4), color.rgb(110, 104, 100))

    def _room(self):
        """Back and side walls with windows; the near (south) side is cut away, with a low glass rail."""
        fx0, fy0, fx1, fy1 = self.fp
        for x in range(fx0, fx1 + 1):                          # back wall
            prop(self.root, 'wallWindow' if (x - fx0) % 3 == 1 else 'wall', self.at(x, fy0 - 0.5), 0, 1.0)
        for y in range(fy0, fy1 + 1):                          # side walls
            for x, angle in ((fx0 - 0.5, 90), (fx1 + 0.5, -90)):
                prop(self.root, 'wallWindow' if (y - fy0) % 3 == 1 else 'wall', self.at(x, y), angle, 1.0)
        w = fx1 - fx0 + 1
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.48, 0.25), (w, 0.5, 0.04), color.rgba(170, 210, 235, 110))
        for x in range(fx0, fx1 + 2, 2):
            box(self.root, self.at(x - 0.5, fy1 + 0.48, 0.25), (0.06, 0.5, 0.06), color.rgb(120, 130, 140))

    def _roof(self):
        fx0, fy0, fx1, fy1 = self.fp
        w, d = fx1 - fx0 + 1, fy1 - fy0 + 1
        par = color.rgb(176, 170, 160)                         # parapet
        box(self.root, self.at((fx0 + fx1) / 2, fy0 - 0.6, 0.35), (w + 1.4, 0.7, 0.4), par)
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.6, 0.2), (w + 1.4, 0.4, 0.4), par)
        for x in (fx0 - 0.6, fx1 + 0.6):
            box(self.root, self.at(x, (fy0 + fy1) / 2, 0.35), (0.4, 0.7, d + 1.2), par)
        walk = set(self.session.level.kinds)
        free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
        near = {c for c in free if any((c[0] + dx, c[1] + dy) in walk for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
        rng = self.rng
        far = sorted(free - near)
        if far:                                                # antenna with a blinking light
            ax, ay = rng.choice(far)
            free.discard((ax, ay))
            box(self.root, self.at(ax, ay, 1.6), (0.08, 3.2, 0.08), color.rgb(70, 70, 76))
            self.beacon = Entity(parent=self.root, model='sphere', position=self.at(ax, ay, 3.25), scale=0.16,
                                 color=color.rgb(255, 60, 50))
        for x, y in sorted(free, key=lambda c: (c not in near, rng.random())):
            if (x, y) not in free or rng.random() > (0.45 if (x, y) in near else 0.25):
                continue
            kind = rng.choice(['ac', 'ac', 'vent', 'tank', 'solar', 'crate'])
            if kind in ('tank', 'solar', 'ac') and not {(x + 1, y), (x, y + 1), (x + 1, y + 1)} <= free:
                kind = rng.choice(['vent', 'crate'])
            if kind == 'ac':                                   # condenser: grey box, two fans on top
                for c in ((x, y), (x + 1, y)):
                    free.discard(c)
                p = self.at(x + 0.5, y, 0.45)
                box(self.root, p, (1.6, 0.9, 0.9), color.rgb(196, 198, 202))
                for dx in (-0.4, 0.4):
                    Entity(parent=self.root, model='sphere', position=p + Vec3(dx, 0.45, 0), scale=(0.62, 0.05, 0.62),
                           color=color.rgb(70, 72, 78))
            elif kind == 'tank':
                for c in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                    free.discard(c)
                p = self.at(x + 0.5, y + 0.5, 0.9)
                Entity(parent=self.root, model='sphere', position=p + Vec3(0, 0.9, 0), scale=(1.7, 0.4, 1.7),
                       color=color.rgb(170, 172, 178))
                box(self.root, p, (1.6, 1.8, 1.6), color.rgb(150, 152, 160))
            elif kind == 'solar':
                for c in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                    free.discard(c)
                box(self.root, self.at(x + 0.5, y + 0.5, 0.45), (1.8, 0.06, 1.6), color.rgb(36, 56, 110),
                    rotation_x=-25)
            elif kind == 'vent':
                free.discard((x, y))
                Entity(parent=self.root, model='sphere', position=self.at(x, y, 0.2), scale=(0.45, 0.4, 0.45),
                       color=color.rgb(80, 80, 88))
            else:
                free.discard((x, y))
                box(self.root, self.at(x, y, 0.35), (0.7, 0.7, 0.7), color.rgb(168, 128, 82))

    def _furnish(self):
        fx0, fy0, fx1, fy1 = self.fp
        bx0, by0, bx1, by1 = self.bbox
        walk = set(self.session.level.kinds)
        free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
        used, rng = set(), self.rng

        def room_for(cells):
            return cells <= free and not any((x + dx, y + dy) in used for x, y in cells
                                             for dx in (-1, 0, 1) for dy in (-1, 0, 1))

        def take(cells):
            used.update(cells)
            free.difference_update(cells)

        def desk(x, y, angle):
            take({(x, y)})
            g = Entity(parent=self.root, position=self.at(x, y), rotation_y=angle)
            prop(g, 'desk', Vec3(0, 0, 0.1))
            prop(g, 'computerScreen', Vec3(0, 0.48, 0.22))
            prop(g, 'chairDesk', Vec3(0, 0, -0.42), 180)

        inside = sorted((c for c in free if bx0 <= c[0] <= bx1 and by0 <= c[1] <= by1), key=lambda c: rng.random())
        meeting = False
        for x, y in inside:
            block = {(x + i, y + j) for i in range(2) for j in range(2)}
            if not meeting and room_for(block):
                meeting = True
                take(block)
                c = self.at(x + 0.5, y + 0.5)
                prop(self.root, 'rugRectangle', c + Vec3(0, 0.01, 0), 0, 1.5)
                prop(self.root, 'tableRound', c, 0, 1.6)
                for a in range(6):
                    ang = a * 60
                    off = Vec3(math.sin(math.radians(ang)), 0, math.cos(math.radians(ang))) * 0.95
                    prop(self.root, 'chair', c + off, ang + 180)
            elif {(x, y), (x, y + 1)} <= free and rng.random() < 0.5:
                desk(x, y, 0)
                desk(x, y + 1, 180)
            elif (x, y) in free and rng.random() < 0.4:
                take({(x, y)})
                prop(self.root, rng.choice(['pottedPlant', 'pottedPlant', 'trashcan', 'cardboardBoxClosed']),
                     self.at(x, y))

        for x in range(fx0 + 1, fx1, 3):                         # back wall: storage
            if room_for({(x, fy0)}) and rng.random() < 0.7:
                take({(x, fy0)})
                prop(self.root, rng.choice(['bookcaseOpen', 'bookcaseClosedDoors', 'bookcaseClosedWide']),
                     self.at(x, fy0 - 0.15), 180)
        for y in range(fy0 + 2, fy1, 2):                         # side walls: desks facing them
            for x, angle in ((fx0, -90), (fx1, 90)):
                if room_for({(x, y)}) and rng.random() < 0.45:
                    desk(x, y, angle)
        for corner in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
            if room_for({corner}):
                take({corner})
                prop(self.root, rng.choice(['pottedPlant', 'lampRoundFloor', 'coatRackStanding']), self.at(*corner))
        if room_for({(fx1 - 1, fy1), (fx1 - 2, fy1)}):            # a sofa corner by the window
            take({(fx1 - 1, fy1), (fx1 - 2, fy1)})
            prop(self.root, 'loungeSofa', self.at(fx1 - 1.5, fy1 + 0.1), 180)

    # ---- the playfield, rebuilt whenever bridges change ----
    def refresh(self):
        for e in list(self.tiles.children):
            destroy(e)
        s = self.session
        office = not self.roof
        for (x, y) in s.level.kinds:
            kind = s.tile_at(x, y)
            p = self.at(x, y, TILE_TOP / 2)
            if kind == 'bridge_closed':                          # barrier across the gap
                Entity(parent=self.tiles, model='cube', position=self.at(x, y, 0.25), scale=(0.9, 0.12, 0.12),
                       color=color.rgb(250, 200, 40))
                for dx in (-0.42, 0.42):
                    box(self.tiles, self.at(x + dx, y, 0.2), (0.06, 0.4, 0.06), color.rgb(60, 60, 66))
                continue
            tex, col = 'textures/concrete', color.rgb(170, 186, 220) if office else color.white
            if kind == 'fragile':
                tex, col = 'textures/fragile', color.white
            elif kind == 'bridge_open':
                tex, col = 'textures/steel', color.white
            top = self.at(x, y, TILE_TOP + 0.005)
            if kind == 'goal':                                   # stairwell going down to the next floor
                box(self.tiles, self.at(x, y, -0.5), (0.96, 1.0, 0.96), color.rgb(40, 36, 34))
                for i in range(6):                               # steps from the floor edge down into the dark
                    box(self.tiles, self.at(x, y - 0.4 + i * 0.16, -0.02 - i * 0.13), (0.84, 0.1, 0.17),
                        color.rgb(240 - i * 26, 226 - i * 26, 196 - i * 24))
                for dx in (-0.46, 0.46):                         # railings
                    box(self.tiles, self.at(x + dx, y, 0.3), (0.05, 0.05, 0.96), color.rgb(120, 96, 70))
                    for dy in (-0.44, 0.44):
                        box(self.tiles, self.at(x + dx, y + dy, 0.15), (0.05, 0.3, 0.05), color.rgb(120, 96, 70))
                continue
            Entity(parent=self.tiles, model='cube', position=p, scale=(0.97, TILE_TOP, 0.97), texture=tex,
                   color=col)
            if kind == 'soft':
                Entity(parent=self.tiles, model='sphere', position=top, scale=(0.5, 0.04, 0.5),
                       color=color.rgb(96, 120, 150))
            elif kind == 'heavy':
                for a in (45, -45):
                    box(self.tiles, top, (0.7, 0.03, 0.12), color.rgb(60, 60, 68), rotation_y=a)
            elif kind == 'split':
                for dx in (-0.22, 0.22):
                    box(self.tiles, top + Vec3(dx, 0, 0), (0.08, 0.03, 0.55), color.rgb(130, 80, 170))

    def destroy(self):
        destroy(self.root)
