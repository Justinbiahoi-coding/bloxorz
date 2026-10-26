"""Opening shot: the camera rides up the outside of the tower, from the night street to the roof at golden hour.

Everything is painted once into a tall "world" surface; each frame only blits a window of it.
Any key skips to the end of the ride; a key at the title starts the game.
"""
import random

import pygame

from . import hud

PAN_MS, TITLE_MS = 5200, 900
SKY = ((0.0, (240, 190, 146)), (0.18, (236, 140, 112)), (0.40, (128, 82, 128)),
       (0.66, (38, 46, 94)), (1.0, (12, 16, 36)))           # top of the world (roof) -> bottom (street)
CONCRETE, GLASS_DARK, LIT = (92, 88, 98), (40, 52, 84), (255, 202, 124)


def _ease(t):
    return t * t * (3 - 2 * t)


def _sky_at(f):
    for (f0, c0), (f1, c1) in zip(SKY, SKY[1:]):
        if f <= f1:
            k = (f - f0) / (f1 - f0)
            return tuple(int(a + (b - a) * k) for a, b in zip(c0, c1))
    return SKY[-1][1]


class Intro:
    def __init__(self, surface, width, height):
        self.surface, self.w, self.h = surface, width, height
        self.k = hud.scale(surface)
        self.tall = height * 4
        self.roof_y = int(height * 0.64)                     # where the roof sits once the ride ends
        self.rng = random.Random(7)
        self.world = self._paint_world()                     # sky only
        self.far = self._paint_skyline(height * 1.3, (40, 44, 80), (190, 160, 110), 0.10)   # parallax layer
        self.near = self._paint_skyline(height * 0.9, (22, 24, 44), LIT, 0.22)
        self.tower = pygame.Surface((width, self.tall), pygame.SRCALPHA)
        self._paint_tower(self.tower)
        self.t0, self.finished = None, False

    # ---- painting (once) ----
    def _paint_world(self):
        w, tall, rng = self.w, self.tall, self.rng
        world = pygame.Surface((w, tall))
        for y in range(tall):
            world.fill(_sky_at(y / tall), (0, y, w, 1))
        for _ in range(420):                                 # stars where the sky is dark
            y = rng.randrange(int(tall * 0.45), tall)
            a = min(255, int(255 * (y / tall - 0.45) * 2.2))
            world.fill((a, a, min(255, a + 20)), (rng.randrange(w), y, 2, 2))
        glow = pygame.Surface((w, int(self.h * 1.2)), pygame.SRCALPHA)   # low sun near the top
        for r in range(int(self.h * 0.6), 0, -12):
            pygame.draw.circle(glow, (255, 214, 150, 6), (int(w * 0.78), int(self.h * 0.35)), r)
        world.blit(glow, (0, 0))
        for _ in range(9):                                   # soft clouds in the upper sky
            cx, cy, r = rng.randrange(w), rng.randrange(int(self.h * 1.6)), rng.randrange(40, 110)
            cloud = pygame.Surface((r * 4, r * 2), pygame.SRCALPHA)
            for dx, dy, s in ((r * 2, r, 1), (r * 1.2, r * 1.2, .7), (r * 2.8, r * 1.15, .75)):
                pygame.draw.circle(cloud, (255, 226, 200, 70), (int(dx), int(dy)), int(r * s))
            world.blit(cloud, (cx - r * 2, cy - r))
        return world

    def _paint_skyline(self, height, color, light, lit_share):
        height = int(height)
        layer = pygame.Surface((self.w, height), pygame.SRCALPHA)
        rng, x = self.rng, -20
        while x < self.w:
            bw, bh = rng.randrange(60, 170), rng.randrange(int(height * 0.25), height)
            pygame.draw.rect(layer, color, (x, height - bh, bw, bh))
            for wy in range(height - bh + 10, height - 6, 16):
                for wx in range(x + 8, x + bw - 8, 14):
                    if rng.random() < lit_share:
                        layer.fill((*light, 200), (wx, wy, 5, 7))
            x += bw + rng.randrange(-10, 20)
        return layer

    def _paint_tower(self, world):
        w, tall, rng, k = self.w, self.tall, self.rng, self.k
        tw = int(min(w * 0.34, 560))
        x0, top = (w - tw) // 2, self.roof_y
        pygame.draw.rect(world, CONCRETE, (x0, top, tw, tall - top))
        band, bay = int(34 * k), int(40 * k)
        for y in range(top + int(18 * k), tall, band):
            f = y / tall
            for x in range(x0 + int(10 * k), x0 + tw - bay // 2, bay):
                lit = rng.random() < 0.08 + 0.6 * f            # more lights lower down, where it is night
                sky = _sky_at(max(0.0, f - 0.1))
                glass = tuple(int(g * 0.5 + s * 0.35) for g, s in zip(GLASS_DARK, sky))
                world.fill(LIT if lit else glass, (x, y, bay - int(14 * k), band - int(12 * k)))
            world.fill((70, 66, 76), (x0, y + band - int(8 * k), tw, 2))
        world.fill((150, 144, 150), (x0, top, 3, tall - top))  # lit left edge
        world.fill((50, 48, 58), (x0 + tw - 4, top, 4, tall - top))
        shade = pygame.Surface((tw, tall - top), pygame.SRCALPHA)
        for i in range(0, tall - top, 4):                   # the facade darkens towards the street
            shade.fill((8, 10, 24, min(170, int(170 * i / (tall - top)))), (0, i, tw, 4))
        world.blit(shade, (x0, top))

        lip = int(10 * k)                                    # parapet and roof silhouettes
        pygame.draw.rect(world, (176, 166, 158), (x0 - lip, top - lip, tw + 2 * lip, lip * 2))
        sil = (58, 54, 66)
        pygame.draw.rect(world, sil, (x0 + tw * 0.40, top - 70 * k, tw * 0.22, 70 * k))          # stair housing
        pygame.draw.rect(world, (255, 196, 120), (x0 + tw * 0.48, top - 46 * k, tw * 0.05, 30 * k))   # its lit door
        pygame.draw.rect(world, sil, (x0 + tw * 0.08, top - 30 * k, tw * 0.16, 30 * k))          # AC units
        pygame.draw.rect(world, sil, (x0 + tw * 0.70, top - 26 * k, tw * 0.12, 26 * k))
        tank_x = x0 + tw * 0.27
        pygame.draw.rect(world, sil, (tank_x, top - 92 * k, tw * 0.10, 52 * k), border_radius=6)   # water tank
        for lx in (tank_x + 4, tank_x + tw * 0.10 - 6):
            pygame.draw.line(world, sil, (lx, top - 40 * k), (lx, top), 3)
        mast_x = int(x0 + tw * 0.88)
        self.beacon = (mast_x, int(top - 150 * k))
        pygame.draw.line(world, sil, (mast_x, top), self.beacon, 4)
        street = int(self.h * 0.06)
        pygame.draw.rect(world, (16, 18, 30), (0, tall - street, w, street))
        for x in range(40, w, 180):                          # street lamps
            pygame.draw.circle(world, (255, 210, 140), (x, tall - street), 3)

    # ---- per frame ----
    def process(self, events):
        now = pygame.time.get_ticks()
        if self.t0 is None:
            self.t0 = now
        t = (now - self.t0) / PAN_MS
        if any(e.type == pygame.KEYDOWN for e in events):
            if t < 1:
                self.t0, t = now - PAN_MS, 1.0               # skip the ride
            else:
                self.finished = True
        p = _ease(min(1.0, t))
        bottom = self.tall - self.h
        cam = int(bottom * (1 - p))
        self.surface.blit(self.world, (0, 0), (0, cam, self.w, self.h))
        far_y = self.h - self.far.get_height() + int(0.5 * (bottom - cam)) - int(self.h * 0.04)
        self.surface.blit(self.far, (0, far_y))                         # moves at half speed: depth
        self.surface.blit(self.near, (0, self.tall - self.near.get_height() - cam))
        self.surface.blit(self.tower, (0, 0), (0, cam, self.w, self.h))
        bx, by = self.beacon[0], self.beacon[1] - cam
        if -20 < by < self.h + 20:
            on = (now // 600) % 2
            pygame.draw.circle(self.surface, (255, 70, 60) if on else (120, 40, 40), (bx, by), 5)

        title_t = (now - self.t0 - PAN_MS + TITLE_MS) / TITLE_MS
        if title_t > 0:
            self._title(min(1.0, title_t), now)

    def _title(self, a, now):
        layer = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        cy = int(self.h * 0.28)
        hud.text(layer, 'BLOXORZ', 96, (40, 30, 40), center=(self.w // 2 + 4, cy + 5))
        hud.text(layer, 'BLOXORZ', 96, hud.PAPER, center=(self.w // 2, cy))
        hud.text(layer, 'T O W E R', 30, hud.INK, center=(self.w // 2, cy + int(70 * self.k)))
        if a >= 1 and (now // 500) % 2 == 0:
            hud.text(layer, 'Press any key', 22, hud.PAPER, center=(self.w // 2, int(self.h * 0.92)))
        layer.set_alpha(int(255 * a))
        self.surface.blit(layer, (0, 0))
