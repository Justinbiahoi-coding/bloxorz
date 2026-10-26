"""The dead on a floor: they circle the playfield, and when the player goes over the edge they converge on the bin.

``Prowlers(floor)`` puts a few voxel zombies on a rectangular beat around the tiles. ``update`` walks them round it;
``converge(point)`` sends them running to spots on a ring around ``point``; ``arrived`` says when they all stand there.
"""
import math
import random

from ursina import Vec3

from .zombie import Zombie, available as zombies_available


class Prowlers:
    def __init__(self, floor, count=4, seed=0):
        self.floor = floor
        self.rng = random.Random(1000 + seed)
        bx0, by0, bx1, by1 = floor.bbox
        fx0, fy0, fx1, fy1 = floor.fp
        m = 1.7                                                  # how far outside the tiles they keep
        x0, x1 = max(bx0 - m, fx0 + 0.6), min(bx1 + m, fx1 - 0.6)
        y0, y1 = max(by0 - m, fy0 + 0.6), min(by1 + m, fy1 - 0.6)
        self.corners = [floor.at(x0, y0), floor.at(x1, y0), floor.at(x1, y1), floor.at(x0, y1)]
        self.lens = [(self.corners[(i + 1) % 4] - self.corners[i]).length() for i in range(4)]
        self.total = sum(self.lens)
        self.members = []
        self.mode, self.slots, self.t = 'prowl', {}, 0.0
        if not zombies_available():
            return
        for i in range(count):
            s = self.total * (i + self.rng.random() * 0.4) / count
            z = Zombie(self.point(s), 0, parent=floor.root, phase=self.rng.uniform(0, 6))
            z.s, z.dir = s, self.rng.choice((-1, 1))
            self.members.append(z)

    def point(self, s):
        s %= self.total
        for i, ln in enumerate(self.lens):
            if s <= ln:
                a, b = self.corners[i], self.corners[(i + 1) % 4]
                return a + (b - a) * (s / ln)
            s -= ln
        return self.corners[0]

    def update(self, dt):
        self.t += dt
        if self.mode == 'prowl':
            for z in self.members:
                ahead = self.point(z.s + z.dir * 1.4)
                if z.walk_to(ahead, dt, speed=0.5) < 0.45:
                    z.s += z.dir * 1.4
                    if self.rng.random() < 0.04:                 # now and then one turns round
                        z.dir = -z.dir
                z.pose(self.t, True)
        elif self.mode == 'converge':
            for z in self.members:
                left = z.walk_to(self.slots[z], dt, speed=3.0)
                z.pose(self.t * 2.4, left > 0.4)

    def converge(self, centre):
        """Send every zombie running to its own spot on a ring round ``centre``."""
        self.mode = 'converge'
        n = max(1, len(self.members))
        start = math.atan2(self.members[0].root.z - centre.z, self.members[0].root.x - centre.x) if self.members else 0
        self.slots = {z: Vec3(centre.x + math.cos(start + i * math.tau / n) * 1.9, self.floor.base,
                              centre.z + math.sin(start + i * math.tau / n) * 1.9) for i, z in enumerate(self.members)}

    @property
    def arrived(self):
        return all((Vec3(z.root.x, 0, z.root.z) - Vec3(self.slots[z].x, 0, self.slots[z].z)).length() < 0.5
                   for z in self.members)

    def face(self, centre):
        for z in self.members:
            d = Vec3(centre.x - z.root.x, 0, centre.z - z.root.z)
            z.root.rotation_y = math.degrees(math.atan2(-d.x, -d.z))

    def lunge(self, k):
        for z in self.members:
            z.lunge = k

    def reset(self):
        """Back on their beat, as they were."""
        for i, z in enumerate(self.members):
            z.s = self.total * (i + self.rng.random() * 0.4) / max(1, len(self.members))
            z.root.position = self.point(z.s)
            z.lunge = 0.0
        self.mode = 'prowl'

    def destroy(self):
        for z in self.members:
            z.destroy()
        self.members = []
