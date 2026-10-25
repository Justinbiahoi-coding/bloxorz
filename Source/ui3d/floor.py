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
        else:                                                  # bare, stained concrete
            box(self.root, c, (w, 0.3, d), color.rgb(34, 34, 36), tex('concrete', 'textures/gravel'),
                texture_scale=(w / 2, d / 2))
        box(self.root, self.at((fx0 + fx1) / 2, fy1 + 0.5, -3.2), (w, 6.2, 0.4), color.rgb(26, 26, 30))

    def _grime(self):
        """Cracks, stains, moss and litter over the bare floor: a storey nobody has cleaned for years."""
        fx0, fy0, fx1, fy1 = self.fp
        rng = self.rng
        for _ in range(int((fx1 - fx0) * (fy1 - fy0) * 0.3)):                         # cracks, some forking
            x, y = rng.uniform(fx0, fx1), rng.uniform(fy0, fy1)
            yaw = rng.uniform(0, 180)
            for seg in range(rng.randint(1, 3)):
                ln = rng.uniform(0.5, 1.6)
                box(self.root, self.at(x, y, 0.004), (0.04, 0.006, ln), color.rgb(22, 20, 19), rotation_y=yaw)
                x += math.sin(math.radians(yaw)) * ln * 0.9
                y -= math.cos(math.radians(yaw)) * ln * 0.9
                yaw += rng.uniform(-35, 35)
        for _ in range(int((fx1 - fx0) * (fy1 - fy0) * 0.12)):                         # damp stains and moss
            x, y = rng.uniform(fx0, fx1), rng.uniform(fy0, fy1)
            moss = rng.random() < 0.35
            sz = rng.uniform(0.8, 2.0)
            box(self.root, self.at(x, y, 0.003), (sz, 0.004, sz * rng.uniform(0.6, 1.2)),
                color.rgba(14, 30, 8, 150) if moss else color.rgba(4, 4, 4, 130), rotation_y=rng.uniform(0, 90))
        free = [(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1) if (x, y) not in self.session.level.kinds]
        for x, y in rng.sample(free, min(len(free), 9)):                              # litter and blood
            name = rng.choice(['SA_Prop_Litter_02', 'SA_Prop_Litter_04', 'SA_Prop_Litter_07', 'SA_Prop_Bloodstain_01',
                               'SA_Prop_Bloodstain_03', 'SA_Prop_CinderBlock_01'])
            prop(self.root, 'zb/' + name, self.at(x + rng.uniform(-.4, .4), y + rng.uniform(-.4, .4), 0.01),
                 rng.uniform(0, 360), rng.uniform(1.2, 1.9) if 'Litter' in name or 'Blood' in name else 2.0
                 ).setColorScale(0.4, 0.4, 0.4, 1)

    def _rubble(self, x, y, n=7):
        """A heap of broken concrete at (x, y) in floor units."""
        rng = self.rng
        for _ in range(n):
            sz = rng.uniform(0.12, 0.42)
            box(self.root, self.at(x + rng.uniform(-0.45, 0.45), y + rng.uniform(-0.45, 0.45), sz * 0.4),
                (sz * rng.uniform(1, 1.8), sz * 0.8, sz), color.rgb(*[rng.randint(40, 62)] * 3), tex('concrete'),
                rotation_y=rng.uniform(0, 360), rotation_x=rng.uniform(-18, 18), rotation_z=rng.uniform(-18, 18))

    def _wall_cell(self, x, y, along_x, rng):
        """One cell of broken wall: standing to a ragged height, a window gap, or collapsed into rubble."""
        r = rng.random()
        t, th = (1.0, 0.45) if along_x else (0.45, 1.0)
        col = color.rgb(*[rng.randint(44, 58)] * 3)
        cx_, cy_ = (x, y)

        def seg(y0, y1):
            box(self.root, self.at(cx_, cy_, (y0 + y1) / 2), (t, y1 - y0, th) if along_x else (th, y1 - y0, t),
                col, tex('concrete'), texture_scale=(1, max(1, (y1 - y0))))

        if r < 0.14:                                           # collapsed
            seg(0, 0.3)
            self._rubble(x, y, 6)
        elif r < 0.40:                                         # window opening, frame left bare
            h = rng.uniform(1.7, 2.1)
            seg(0, 0.55)
            seg(1.35, h)
        else:
            h = rng.uniform(1.2, 2.2)
            seg(0, h)
            if rng.random() < 0.5:                             # a jagged break and a rebar stub on top
                box(self.root, self.at(x + rng.uniform(-.2, .2), y + rng.uniform(-.2, .2), h + 0.1),
                    (0.5, 0.25, 0.4), col, tex('concrete'), rotation_y=rng.uniform(-30, 30), rotation_z=rng.uniform(-20, 20))
                Entity(parent=self.root, model=CYL, position=self.at(x + rng.uniform(-.3, .3), y, h + 0.35),
                       scale=(0.03, 0.6, 0.03), color=color.rgb(96, 62, 44), rotation_z=rng.uniform(-25, 25))

    def _room(self):
        """Ruined back and side walls (ragged, with holes and heaps of rubble); the near side is open, with a
        few barricades. Emergency light pools and the grime over the floor finish it."""
        fx0, fy0, fx1, fy1 = self.fp
        rng = self.rng
        for x in range(fx0, fx1 + 1):                          # back wall
            self._wall_cell(x, fy0 - 0.5, True, rng)
        for y in range(fy0, fy1 + 1):                          # side walls
            for x in (fx0 - 0.5, fx1 + 0.5):
                self._wall_cell(x, y, False, rng)
        for x in range(fx0 + 1, fx1, 4):                       # the open side: a broken line of barricades
            if rng.random() < 0.75:
                (prop(self.root, 'zb/' + rng.choice(['SA_Prop_Barrier_01', 'SA_Prop_Barrier_03', 'SA_Prop_Fence_Wood_Damaged_01',
                                                    'SA_Prop_Crate_01', 'SA_Prop_Fence_Brick_01']),
                     self.at(x + rng.uniform(-.3, .3), fy1 + 0.48), rng.uniform(-14, 14), 1.1)).setColorScale(0.4, 0.4, 0.4, 1)
        self._grime()
        for x in range(fx0 + 2, fx1, 5):                       # sickly light pools: dim amber, the odd red
            for y in range(fy0 + 1, fy1, 5):
                red = rng.random() < 0.3
                glow(self.root, self.at(x, y, 0.005), (2.4, 0.005, 2.4),
                     color.rgba(255, 70, 50, 30) if red else color.rgba(255, 190, 120, 22), model='circle', rotation_x=90)

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
        """Wrecked furniture, barricades and a squatters' corner, only in the gaps: plenty of bare floor stays."""
        fx0, fy0, fx1, fy1 = self.fp
        bx0, by0, bx1, by1 = self.bbox
        walk = set(self.session.level.kinds)
        free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
        used, rng = set(), self.rng
        grime = (0.4, 0.38, 0.36, 1)

        def room_for(cells, gap=1):
            return cells <= free and not any((x + dx, y + dy) in used for x, y in cells
                                             for dx in range(-gap, gap + 1) for dy in range(-gap, gap + 1))

        def take(cells):
            used.update(cells)
            free.difference_update(cells)

        def old(name, pos, yaw=0, k=1.0, tilt=0.0):
            h = prop(self.root, 'zb/' + name if name.startswith('SA_') else name, pos, yaw, k)
            h.setColorScale(*grime)
            h.rotation_z = tilt
            return h

        groups = 0
        inside = sorted((c for c in free if bx0 <= c[0] <= bx1 and by0 <= c[1] <= by1), key=lambda c: rng.random())
        for x, y in inside:
            if groups >= 3:
                break
            block = {(x + i, y + j) for i in range(2) for j in range(2)}
            if groups == 0 and room_for(block):                # a squatters' camp: couch, mattress, fire, crates
                take(block)
                c = self.at(x + 0.5, y + 0.5)
                old('SA_Prop_Mattress_02', c + Vec3(-0.25, 0.01, 0.1), 20, 1.5)
                old('SA_Prop_Couch_Damaged_01', c + Vec3(0.35, 0, -0.5), 180, 1.0)
                old('SA_Prop_Campfire_01', c + Vec3(0.3, 0, 0.45), 0, 1.0)
                glow(self.root, c + Vec3(0.3, 0.012, 0.45), (1.4, 0.005, 1.4), color.rgba(255, 140, 60, 40), model='circle',
                     rotation_x=90)
                old('SA_Prop_Crate_01', c + Vec3(-0.6, 0, -0.45), 15, 0.9)
                groups += 1
            elif room_for({(x, y), (x, y + 1)}, gap=2):        # a toppled desk and a broken chair
                take({(x, y), (x, y + 1)})
                old('desk', self.at(x, y, 0.35), rng.uniform(0, 180), 1.0, 78)
                old('SA_Prop_Chair_Damaged_0%d' % rng.randint(1, 3), self.at(x, y + 1), rng.uniform(0, 360), 1.2)
                self._rubble(x, y + 0.4, 3)
                groups += 1
            elif room_for({(x, y)}, gap=2) and rng.random() < 0.6:
                take({(x, y)})
                old(rng.choice(['SA_Prop_Barrel_01', 'SA_Prop_Barrel_02', 'SA_Prop_Dumpster_01', 'SA_Prop_Crate_01',
                                'SA_Prop_BodyBag_03']), self.at(x, y), rng.uniform(0, 360), 1.0)
                groups += 1
        for x in range(fx0 + 1, fx1, 4):                       # back wall: a toppled shelf, the odd barricade
            if room_for({(x, fy0)}) and rng.random() < 0.6:
                take({(x, fy0)})
                if rng.random() < 0.5:
                    old(rng.choice(['bookcaseOpen', 'bookcaseClosedDoors']), self.at(x, fy0 - 0.1, 0.4), 180, 1.0, 72)
                else:
                    old('SA_Prop_Barrier_02', self.at(x, fy0), 0, 1.2)
        for corner in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):
            if room_for({corner}):
                take({corner})
                old(rng.choice(['SA_Prop_Barrel_02', 'SA_Prop_Crate_01', 'SA_Prop_Dumpster_01']), self.at(*corner),
                    rng.uniform(0, 360), 1.0)
                self._rubble(corner[0], corner[1], 4)

    # ---- the playfield, rebuilt whenever bridges change ----
    def refresh(self):
        for e in list(self.tiles.children):
            destroy(e)
        s = self.session
        office = not self.roof
        path_tex = tex('concrete' if office else 'paver', 'textures/concrete')
        path_col = color.rgb(96, 100, 112) if office else color.rgb(235, 232, 225)   # worn, chipped slabs
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
