"""The ruined city and the street in front of the tower, used by the opening cutscene (daytime).

The street runs along -z away from the tower's entrance. Its far end is a checkpoint gate (two guard towers,
wire fences, a few of the dead on watch); both sides are lined with the coloured ruins from Zombie Barricades
(models/zb, used with the author's permission, see docs/CREDITS.md), with burnt cars and barricades on the
road. ``_city`` spreads more blocks, autumn trees and a helipad out beyond for the aerial shot. Everything is
parented to one entity so the cutscene can throw it away in one call.
"""
import math
import random

from ursina import Entity, Sky, Vec3, color

from .floor import BOX, CYL, glow, prop, tex
from .world import ASSETS

ZB = ASSETS / 'models' / 'zb'
S = 1.7                                                     # the pack's buildings are small next to our cells
SIDE = ('SA_Bld_OfficeBlue_03', 'SA_Bld_TownHouseLarge_01', 'SA_Bld_OfficeWhite_02', 'SA_Bld_Apartment_Damaged_01',
        'SA_Bld_ShopOld_Damaged_01', 'SA_Bld_Office_Damaged_01', 'SA_Bld_OfficeBlue_04', 'SA_Bld_TownHouse_01',
        'SA_Bld_HospitalBuilding_Damaged_01', 'SA_Bld_OfficeWhite_03', 'SA_Bld_Church_Damaged_01')
CARS = ('SA_Prop_BurntBrown_Car_01', 'SA_Prop_BurntBlack_Van_01', 'SA_Prop_BurntBrown_Bus_01',
        'SA_Prop_BurntBlack_Ute_01', 'SA_Prop_CarRolled_01', 'SA_Prop_BurntBrown_FamilyCar_01')
JUNK = ('SA_Prop_Barrier_01', 'SA_Prop_Dumpster_01', 'SA_Prop_Crate_01', 'SA_Prop_Barrel_01', 'SA_Prop_Barrier_03')
TREES = ('Prop_Tree_Apple', 'Prop_Tree_Lemon', 'Prop_Tree_Orange')
AUTUMN = ((1.0, 0.62, 0.3), (0.95, 0.8, 0.3), (0.78, 0.42, 0.22), (0.6, 0.72, 0.3))
ROAD, KERB, GRASS = color.rgb(92, 94, 102), color.rgb(176, 172, 160), color.rgb(116, 140, 72)


def available():
    return ZB.exists() and (ZB / 'SA_Bld_OfficeBlue_03.glb').exists()


class Street:
    """``length`` cells of street reaching out from (cx, 0, z0) towards -z."""

    def __init__(self, cx, z0, length=80, width=13):
        self.root = Entity()
        self.cx, self.z0, self.length, self.width = cx, z0, length, width
        self.gate_z = z0 - length + 14
        rng = random.Random(21)
        Sky(parent=self.root)                                                               # the default blue day sky
        box_ = lambda *a, **k: Entity(parent=self.root, model=BOX, *a, **k)
        box_(position=(cx, -0.25, z0 - 40), scale=(520, 0.2, 520), color=GRASS,
             texture=tex('grass'), texture_scale=(120, 120))                                # the whole county
        box_(position=(cx, -0.1, z0 - length / 2), scale=(width, 0.2, length), color=ROAD,
             texture=tex('roof'), texture_scale=(width / 4, length / 4))                    # tarmac
        for i in range(int(length / 6)):                                                    # centre line
            glow(self.root, Vec3(cx, 0.02, z0 - 3 - i * 6), (0.22, 0.01, 2.2), color.rgb(236, 214, 130))
        for side in (-1, 1):                                                                # kerbs and pavements
            box_(position=(cx + side * (width / 2 + 0.9), 0.1, z0 - length / 2), scale=(2.2, 0.35, length),
                 color=KERB, texture=tex('concrete'), texture_scale=(1, length / 4))
        self.props = []
        for i in range(7):                                                                  # ruins down both sides
            for side in (-1, 1):
                z = z0 - 8 - i * 11 - rng.uniform(0, 2)
                name = SIDE[(i * 2 + (side > 0)) % len(SIDE)]
                yaw = -90 * side + rng.uniform(-3, 3)                                       # the front faces the road
                self.props.append(prop(self.root, 'zb/' + name, Vec3(cx + side * (width / 2 + 5 + 5 * S), 0, z),
                                       yaw, S))
        for i in range(10):                                                                 # wrecks and junk on the road
            z = z0 - 20 - rng.uniform(0, length - 34)                                       # keep the near end clear
            x = cx + rng.uniform(-width / 2 + 1.5, width / 2 - 1.5)
            prop(self.root, 'zb/' + (CARS if i % 2 == 0 else JUNK)[i // 2 % 5], Vec3(x, 0, z),
                 rng.uniform(0, 360) if i % 2 else rng.choice((88, 92, 268)), 1.4)
        for i in range(10):                                                                 # trees along the pavements
            side = -1 if i % 2 else 1
            t = prop(self.root, 'zb/' + TREES[i % 3], Vec3(cx + side * (width / 2 + 2.2), 0, z0 - 6 - i * 7.5),
                     rng.uniform(0, 360), rng.uniform(2.4, 3.2))
            t.setColorScale(*rng.choice(AUTUMN), 1)
        self.fires = []
        for i, z in enumerate(z0 - 12 - 17 * i for i in range(3)):                          # burning barrels
            x = cx + (self.width / 2 - 1.0) * (1 if i % 2 else -1)
            Entity(parent=self.root, model=CYL, position=(x, 0.35, z), scale=(0.55, 0.7, 0.55),
                   color=color.rgb(120, 70, 50), texture=tex('corrugated'))
            f = glow(self.root, Vec3(x, 0.85, z), (0.5, 0.6, 0.5), color.rgb(255, 150, 60), model='sphere')
            halo = glow(self.root, Vec3(x, 0.9, z), (2.4, 0.02, 2.4), color.rgba(255, 140, 50, 40), model='circle',
                        rotation_x=90)
            self.fires.append((f, halo, random.Random(i).uniform(0, 6)))
        self._gate(rng)
        self.city = self._city(rng)
        self.bin = self._bin(cx - 2.5, z0 - 26)                                             # the hiding place

    def _gate(self, rng):
        """The checkpoint: two guard towers either side of the road, wire fences, a bus across half of it."""
        cx, w, gz = self.cx, self.width, self.gate_z
        for side in (-1, 1):
            prop(self.root, 'zb/SA_Prop_GuardTower_01', Vec3(cx + side * (w / 2 + 1.0), 0, gz), 0, 2.4)
            for j in range(1, 6):
                prop(self.root, 'zb/SA_Prop_Fence_Wire_Full_01', Vec3(cx + side * (w / 2 + 1.0 + j * 2.6), 0, gz - 1.0),
                     90, 1.4)
        prop(self.root, 'zb/SA_Prop_BurntBrown_Bus_01', Vec3(cx + 2.4, 0, gz + 9), 78, 1.7)
        for k in range(4):
            prop(self.root, 'zb/SA_Prop_Barrier_0%d' % (1 + k % 3), Vec3(cx - 3.6 + k * 1.5, 0, gz + 3),
                 rng.uniform(-10, 10), 1.8)
        self.gate_spots = [Vec3(cx - 2.4, 0, gz + 2.0), Vec3(cx + 2.8, 0, gz + 1.2)]

    def _city(self, rng):
        """Blocks of ruins, trees and a helipad spread around the street, for the aerial shot. They sit on their
        own entity so the street shots need not pay for them twice."""
        root = Entity(parent=self.root)
        cx, z0, w, length = self.cx, self.z0, self.width, self.length
        placed = []
        for _ in range(240):
            if len(placed) >= 34:
                break
            ang, r = rng.uniform(0, math.tau), math.sqrt(rng.uniform(0.12, 1)) * 108
            x, z = cx + math.cos(ang) * r, z0 - 24 + math.sin(ang) * r
            if abs(x - cx) < w / 2 + 26 and z0 - length - 8 < z < z0 + 8:
                continue                                           # keep the street and its rows clear
            if any((x - px) ** 2 + (z - pz) ** 2 < 24 ** 2 for px, pz in placed):
                continue
            placed.append((x, z))
            prop(root, 'zb/' + SIDE[len(placed) % len(SIDE)], Vec3(x, 0, z), rng.choice((0, 90, 180, 270)), S)
        for _ in range(60):                                        # a wood of autumn trees on the grass
            ang, r = rng.uniform(0, math.tau), math.sqrt(rng.uniform(0.05, 1)) * 112
            x, z = cx + math.cos(ang) * r, z0 - 24 + math.sin(ang) * r
            if abs(x - cx) < w / 2 + 3 and z0 - length - 8 < z < z0 + 8:
                continue
            if any((x - px) ** 2 + (z - pz) ** 2 < 12 ** 2 for px, pz in placed):
                continue
            t = prop(root, 'zb/' + TREES[int(r) % 3], Vec3(x, 0, z), rng.uniform(0, 360), rng.uniform(2.6, 4.0))
            t.setColorScale(*rng.choice(AUTUMN), 1)
        for _ in range(30):                                        # roads full of wreckage
            ang, r = rng.uniform(0, math.tau), math.sqrt(rng.uniform(0.1, 1)) * 100
            prop(root, 'zb/' + rng.choice(CARS), Vec3(cx + math.cos(ang) * r, 0, z0 - 24 + math.sin(ang) * r),
                 rng.uniform(0, 360), 1.5)
        self.block_spots = placed
        self.pad = self._helipad(root, placed)
        return root

    def _helipad(self, root, placed):
        """A tall office block beside the tower with a helipad on its roof: the aerial shot ends on it (and
        the helicopter lands there at the end of the game)."""
        x, z = self.cx + 42, self.z0 - 18
        placed[:] = [p for p in placed if (p[0] - x) ** 2 + (p[1] - z) ** 2 > 30 ** 2]
        prop(root, 'zb/SA_Bld_OfficeWhite_03', Vec3(x, 0, z), 90, S)
        top = 11.4 * S                                             # the model is 11.4 tall before scaling
        prop(root, 'zb/SA_Bld_HospitalBuildingMain_HeliPad_01', Vec3(x, top, z), 0, 1.9)
        return Vec3(x, top, z)

    def _bin(self, x, z):
        """A plain municipal bin: the survivor dives into this one and comes out as the character."""
        holder = Entity(parent=self.root, position=(x, 0, z))
        body = color.rgb(126, 132, 138)
        Entity(parent=holder, model=CYL, position=(0, 0.95, 0), scale=(0.92, 1.75, 0.92), color=body,
               texture=tex('corrugated'), texture_scale=(2, 1))
        for y in (0.45, 1.3):                                        # pressed ribs
            Entity(parent=holder, model=CYL, position=(0, y, 0), scale=(0.97, 0.07, 0.97),
                   color=color.rgb(96, 100, 108))
        Entity(parent=holder, model=CYL, position=(0, 0.1, 0), scale=(0.99, 0.18, 0.99),
               color=color.rgb(84, 88, 96))                          # base rim
        self.lid = Entity(parent=holder, model=CYL, position=(0, 1.9, 0), scale=(1.0, 0.12, 1.0),
                          color=color.rgb(150, 156, 162))
        Entity(parent=self.lid, model=CYL, position=(0, 0.6, 0), scale=(0.3, 0.9, 0.3),
               color=color.rgb(96, 100, 108))                        # handle
        return holder

    def flicker(self, t):
        for f, halo, phase in self.fires:
            k = 0.82 + 0.18 * math.sin(t * 9 + phase) + 0.08 * math.sin(t * 23 + phase * 2)
            f.scale = Vec3(0.5, 0.6, 0.5) * k
            halo.color = color.rgba(255, 140, 50, int(40 * k))

    def destroy(self):
        from ursina import destroy
        destroy(self.root)
