"""The ruined city around the tower, used by the opening cutscene (daytime, after the Zombie Barricades trailer).

One avenue runs along -z from the tower's entrance, with a checkpoint gate at its far end. A grid of cross
streets and city blocks spreads out on both sides: each block is a pavement slab ringed by rows of the game's
own buildings facing the street (models/zb, used with the author's permission, see docs/CREDITS.md), with a
green courtyard of autumn trees inside. Crosswalks, litter, burnt cars and barricades dress the roads.
Everything is parented to one entity so the cutscene can throw it away in one call.
"""
import json
import math
import random

from ursina import Entity, Sky, Vec3, color

from .floor import BOX, CYL, glow, prop, tex
from .world import ASSETS

ZB = ASSETS / 'models' / 'zb'
G = 1.15                                                    # building scale
# (mesh, width along the facade, depth): measured from the converted models
BUILDINGS = (('SA_Bld_TownHouse_01', 3.9, 7.6), ('SA_Bld_TownHouse_02', 3.9, 7.6), ('SA_Bld_TownHouseLarge_01', 7.7, 7.6),
             ('SA_Bld_OfficeBlue_03', 5.8, 6.4), ('SA_Bld_OfficeBlue_02', 5.8, 6.4), ('SA_Bld_OfficeWhite_02', 5.8, 6.4),
             ('SA_Bld_OfficeWhite_03', 5.8, 6.4), ('SA_Bld_OfficeGrey_02', 5.8, 6.4), ('SA_Bld_Apartment_Damaged_01', 6.2, 6.2),
             ('SA_Bld_Shop_Damaged_01', 6.9, 6.8), ('SA_Bld_ShopOld_Damaged_01', 9.7, 5.9), ('SA_Bld_ShopSmall_01', 5.8, 5.4),
             ('SA_Bld_Office_Damaged_01', 8.3, 8.7), ('SA_Bld_PoliceStation_Damaged_01', 10.2, 6.3),
             ('SA_Bld_Diner_Damaged_01', 10.2, 4.4), ('SA_Bld_Church_Damaged_01', 5.4, 9.7),
             ('SA_Bld_TownHall_Damaged_01', 13.9, 9.9), ('SA_Bld_OfficeOld_01', 3.9, 4.7))
ROWHOUSES = (('SA_Bld_TownHouse_01', 3.9, 7.6), ('SA_Bld_TownHouse_02', 3.9, 7.6))
CARS = ('SA_Prop_BurntBrown_Car_01', 'SA_Prop_BurntBlack_Van_01', 'SA_Prop_BurntBrown_Bus_01',
        'SA_Prop_BurntBlack_Ute_01', 'SA_Prop_CarRolled_01', 'SA_Prop_BurntBrown_FamilyCar_01',
        'SA_Prop_BurntBrown_Ute_01', 'SA_Prop_BurntBlack_FamilyCar_01')
JUNK = ('SA_Prop_Barrier_01', 'SA_Prop_Dumpster_01', 'SA_Prop_Crate_01', 'SA_Prop_Barrel_01', 'SA_Prop_Barrier_03')
LITTER = ('SA_Prop_Litter_02', 'SA_Prop_Litter_04', 'SA_Prop_Litter_07')
TREES = ('Prop_Tree_Apple', 'Prop_Tree_Lemon', 'Prop_Tree_Orange')
AUTUMN = ((1.0, 0.62, 0.3), (0.95, 0.8, 0.3), (0.78, 0.42, 0.22), (0.6, 0.72, 0.3))
ASPHALT, PAVE, GRASS = color.rgb(70, 72, 80), color.rgb(168, 164, 152), color.rgb(112, 138, 70)
ROAD_W, BLOCK, PAV = 14.0, 40.0, 2.4
PITCH = BLOCK + ROAD_W


def available():
    return ZB.exists() and (ZB / 'SA_Bld_OfficeBlue_03.glb').exists()


class Street:
    """The avenue (``length`` cells from (cx, 0, z0) towards -z) and the city block grid around it."""

    def __init__(self, cx, z0, length=160, width=ROAD_W):
        self.root = Entity()
        self.cx, self.z0, self.length, self.width = cx, z0, length, width
        self.gate_z = z0 - length + 16
        self.props, self.block_spots = [], []
        rng = random.Random(21)
        Sky(parent=self.root)                                                                # the default blue day sky
        box_ = lambda *a, **k: Entity(parent=self.root, model=BOX, *a, **k)
        box_(position=(cx, -0.3, z0 - length / 2), scale=(900, 0.2, 900), color=ASPHALT,
             texture=tex('roof'), texture_scale=(220, 220))                                  # asphalt everywhere
        self.fires = []
        cols = (-2, -1, 1, 2)                                                                # block columns either side
        rows = int((length - 8) // PITCH) + 1
        for r in range(-1, rows + 1):
            zc = z0 - 6 - BLOCK / 2 - r * PITCH
            for c in cols:
                xc = cx + (width / 2 + BLOCK / 2) * (1 if c > 0 else -1) + (abs(c) - 1) * PITCH * (1 if c > 0 else -1)
                self._block(xc, zc, rng, (r + c) % 3 == 0 and abs(c) > 1)
            zr = zc - BLOCK / 2 - ROAD_W / 2                                                 # cross street centre
            self._lines(zr)
        for i in range(int(length / 8)):                                                     # avenue centre line
            glow(self.root, Vec3(cx, 0.03, z0 - 4 - i * 8), (0.25, 0.01, 3.4), color.rgb(236, 214, 130))
        self._litter(rng, length)
        self._avenue(rng)
        self._gate(rng)
        self.city = Entity(parent=self.root)
        pad = self._helipad()
        self.pad = pad
        self.bin = self._bin(cx - 2.5, z0 - 26)                                              # the hiding place

    def _block(self, xc, zc, rng, park):
        """A pavement slab with buildings (or, in a park, trees only) round its rim, courtyard in the middle."""
        Entity(parent=self.root, model=BOX, position=(xc, 0.1, zc), scale=(BLOCK, 0.4, BLOCK), color=PAVE,
               texture=tex('concrete'), texture_scale=(BLOCK / 4, BLOCK / 4))
        Entity(parent=self.root, model=BOX, position=(xc, 0.32, zc), scale=(BLOCK - 2 * PAV - 18, 0.1, BLOCK - 2 * PAV - 18),
               color=GRASS, texture=tex('grass'), texture_scale=(4, 4))
        self.block_spots.append((xc, zc))
        # the four edges: (facing yaw, unit vector along the edge, outward normal)
        for yaw, ax, az, nx, nz in ((0, 1, 0, 0, -1), (180, -1, 0, 0, 1), (90, 0, 1, 1, 0), (-90, 0, -1, -1, 0)):
            span, inset, used = BLOCK - 2 * PAV - 5, PAV + 4.2, 0.0
            if park:
                continue
            row = ROWHOUSES if rng.random() < 0.4 else BUILDINGS
            while True:
                name, w, d = rng.choice(row)
                w, d = w * G, d * G
                if used + w > span:
                    break
                s = -span / 2 + used + w / 2                                                 # along the edge
                off = BLOCK / 2 - inset - (d - 7.0 * G) * 0.0                                # towards the street
                self.props.append(prop(self.root, 'zb/' + name,
                                       Vec3(xc + ax * s + nx * (off - d / 2 + 2.2),
                                            0.3, zc + az * s + nz * (off - d / 2 + 2.2)), yaw, G))
                used += w + 0.5
        for _ in range(7 if not park else 18):                                              # courtyard trees
            t = prop(self.root, 'zb/' + rng.choice(TREES),
                     Vec3(xc + rng.uniform(-9, 9), 0.3, zc + rng.uniform(-9, 9)) if not park else
                     Vec3(xc + rng.uniform(-16, 16), 0.3, zc + rng.uniform(-16, 16)),
                     rng.uniform(0, 360), rng.uniform(2.4, 3.4))
            t.setColorScale(*rng.choice(AUTUMN), 1)

    def _lines(self, z):
        """Crosswalk stripes across the avenue and the cross street at one intersection."""
        cx, w = self.cx, self.width
        for side in (-1, 1):
            for i in range(-3, 4):
                glow(self.root, Vec3(cx + i * 1.8, 0.03, z + side * (ROAD_W / 2 + 0.2)), (0.9, 0.01, 2.2),
                     color.rgb(238, 238, 230))
        for i in range(10):                                                                  # cross street centre line
            for sgn in (-1, 1):
                glow(self.root, Vec3(cx + sgn * (ROAD_W / 2 + 4 + i * 8), 0.03, z), (3.4, 0.01, 0.25), color.rgb(236, 214, 130))

    def _litter(self, rng, length):
        for _ in range(170):
            prop(self.root, 'zb/' + rng.choice(LITTER),
                 Vec3(self.cx + rng.uniform(-60, 60), 0.04, self.z0 - rng.uniform(0, length)), rng.uniform(0, 360), 4.5)

    def _avenue(self, rng):
        cx, z0, length, w = self.cx, self.z0, self.length, self.width
        for i in range(14):                                                                  # wrecks and junk on the road
            z = z0 - 20 - rng.uniform(0, length - 40)
            x = cx + rng.uniform(-w / 2 + 2, w / 2 - 2)
            if abs(z - (z0 - 26)) < 16:                                                      # keep the bin's shots clear
                continue
            prop(self.root, 'zb/' + (CARS if i % 2 == 0 else JUNK)[i // 2 % 5], Vec3(x, 0.02, z),
                 rng.choice((88, 92, 268, 272)) if i % 2 == 0 else rng.uniform(0, 360), 1.5)
        for i, z in enumerate(z0 - 12 - 22 * i for i in range(5)):                           # burning barrels
            x = cx + (w / 2 - 1.2) * (1 if i % 2 else -1)
            Entity(parent=self.root, model=CYL, position=(x, 0.35, z), scale=(0.55, 0.7, 0.55),
                   color=color.rgb(120, 70, 50), texture=tex('corrugated'))
            f = glow(self.root, Vec3(x, 0.85, z), (0.5, 0.6, 0.5), color.rgb(255, 150, 60), model='sphere')
            halo = glow(self.root, Vec3(x, 0.9, z), (2.4, 0.02, 2.4), color.rgba(255, 140, 50, 40), model='circle',
                        rotation_x=90)
            self.fires.append((f, halo, random.Random(i).uniform(0, 6)))

    def _gate(self, rng):
        """The checkpoint: two guard towers either side of the road, wire fences, a bus across half of it."""
        cx, w, gz = self.cx, self.width, self.gate_z
        for side in (-1, 1):
            prop(self.root, 'zb/SA_Prop_GuardTower_01', Vec3(cx + side * (w / 2 + 1.0), 0, gz), 0, 2.4)
            for j in range(1, 6):
                prop(self.root, 'zb/SA_Prop_Fence_Wire_Full_01', Vec3(cx + side * (w / 2 + 1.0 + j * 2.6), 0, gz - 1.0),
                     90, 1.4)
        prop(self.root, 'zb/SA_Prop_BurntBrown_Bus_01', Vec3(cx + 4.8, 0, gz + 9), 78, 1.7)
        for k in range(4):
            prop(self.root, 'zb/SA_Prop_Barrier_0%d' % (1 + k % 3), Vec3(cx - 3.6 + k * 1.5, 0, gz + 3),
                 rng.uniform(-10, 10), 1.8)
        self.gate_spots = [Vec3(cx - 2.4, 0, gz + 2.0), Vec3(cx + 2.8, 0, gz + 1.2)]

    def _helipad(self):
        """A tall office block on the second block row with a helipad on its roof: the aerial shot ends on it
        (and the helicopter lands there at the end of the game)."""
        x, z = self.cx + (self.width / 2 + BLOCK / 2) + 4, self.z0 - 6 - BLOCK / 2 - PITCH
        prop(self.root, 'zb/SA_Bld_OfficeWhite_03', Vec3(x, 0.3, z), 90, 1.9)
        top = 11.4 * 1.9 + 0.3
        prop(self.root, 'zb/SA_Bld_HospitalBuildingMain_HeliPad_01', Vec3(x, top, z), 0, 1.9)
        return Vec3(x, top, z)

    def _bin(self, x, z):
        """The street bin (zfr_lowpoly_trashbin, split into body and lid by tools/blender_bin.py).

        holder (position of the bin's centre) -> spin (rolling about the world x axis once it lies down) ->
        lie (tipped over by rotation_z) -> the parts. standing: ``tip(0)``; lying across x: ``tip(90)``."""
        info = json.loads((ASSETS / 'models' / 'bin' / 'bin.json').read_text())
        k = 0.9
        self.bin_h, self.bin_r = info['height'] * k, info['width'] / 2 * k
        holder = Entity(parent=self.root, position=(x, self.bin_h / 2, z))
        self.bin_spin = Entity(parent=holder)
        self.bin_lie = Entity(parent=self.bin_spin)
        for name, pos in (('bin_body', (0, 0, 0)), ('bin_lid', info['lid'])):
            e = Entity(parent=self.bin_lie, model='models/bin/' + name, scale=k,
                       position=(pos[0] * k, pos[1] * k - self.bin_h / 2, pos[2] * k))
            for m in e.findAllMaterials():
                m.setMetallic(0)
        return holder

    def tip_bin(self, theta, base_x, base_z, toward=-1):
        """Knock the bin over about its base edge on the ``toward`` side (x direction): theta 0 = standing,
        90 = lying across x. ``base_x``/``base_z`` is where it stood. Returns the centre it ends up at."""
        h, r = self.bin_h, self.bin_r
        th = math.radians(theta)
        px = base_x + toward * r                                        # the edge it pivots on
        cx = px + (-toward) * (r * math.cos(th)) + toward * (h / 2) * math.sin(th)
        cy = r * math.sin(th) + (h / 2) * math.cos(th)
        self.bin.position = Vec3(cx, cy, base_z)
        self.bin_lie.rotation_z = -toward * theta                       # towards -x is a positive turn about z
        return self.bin.position

    def flicker(self, t):
        for f, halo, phase in self.fires:
            k = 0.82 + 0.18 * math.sin(t * 9 + phase) + 0.08 * math.sin(t * 23 + phase * 2)
            f.scale = Vec3(0.5, 0.6, 0.5) * k
            halo.color = color.rgba(255, 140, 50, int(40 * k))

    def destroy(self):
        from ursina import destroy
        destroy(self.root)
