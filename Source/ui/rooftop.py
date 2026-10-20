"""Rooftop look: procedural sky, concrete tiles with an edge, metallic block. No image assets."""
import math
import random

import pygame

SKY_TOP, SKY_BOTTOM = (96, 158, 226), (214, 234, 250)
CONCRETE, CONCRETE_LINE, CONCRETE_SIDE = (204, 196, 184), (168, 160, 148), (122, 116, 106)
PIT, RING = (28, 30, 40), (245, 245, 245)
BLOCK, BLOCK_LIGHT, BLOCK_DARK = (52, 98, 186), (150, 190, 245), (26, 52, 112)
HINT = (255, 150, 40)


def sky(size, seed=7):
    """Vertical gradient with soft clouds, built once and blitted every frame."""
    w, h = size
    surf = pygame.Surface(size)
    for y in range(h):
        t = y / h
        surf.fill(tuple(int(a + (b - a) * t) for a, b in zip(SKY_TOP, SKY_BOTTOM)), (0, y, w, 1))
    rng = random.Random(seed)
    cloud = pygame.Surface(size, pygame.SRCALPHA)
    for _ in range(14):
        cx, cy, r = rng.randrange(w), rng.randrange(h), rng.randrange(30, 70)
        for dx, dy, k in ((0, 0, 1), (r * .8, r * .1, .75), (-r * .8, r * .15, .7), (r * .3, -r * .35, .7)):
            pygame.draw.circle(cloud, (255, 255, 255, 150), (int(cx + dx), int(cy + dy)), int(r * k))
    surf.blit(cloud, (0, 0))
    return surf


FRAGILE, BRIDGE = (226, 170, 110), (150, 108, 64)
SOFT, HEAVY, SPLIT = (96, 120, 150), (70, 70, 78), (120, 70, 150)


def tile(surf, rect, kind, edge_below, texture=None):
    """One tile. ``edge_below``: the cell under it is empty, so show the slab's side face."""
    if kind in ('void', 'bridge_closed'):
        if kind == 'bridge_closed':                          # barrier across a gap that a switch can open
            bar = rect.inflate(-rect.w // 8, -rect.h * 3 // 5)
            pygame.draw.rect(surf, (250, 200, 40), bar)
            step = max(4, bar.w // 6)
            old_clip = surf.get_clip()
            surf.set_clip(bar)
            for x in range(bar.x - bar.h, bar.right, step * 2):
                pygame.draw.polygon(surf, (30, 30, 34), [(x, bar.bottom), (x + bar.h, bar.y), (x + bar.h + step, bar.y), (x + step, bar.bottom)])
            surf.set_clip(old_clip)
            pygame.draw.rect(surf, (30, 30, 34), bar, 1)
            for px in (bar.x, bar.right - 4):
                pygame.draw.rect(surf, (90, 90, 96), (px, bar.y - 3, 4, bar.h + 6))
        return
    depth = max(4, rect.height // 4)
    if edge_below:
        pygame.draw.rect(surf, CONCRETE_SIDE, (rect.x, rect.bottom, rect.width, depth))
    if texture is not None and texture.get_size() == rect.size:
        surf.blit(texture, rect.topleft)
    else:
        pygame.draw.rect(surf, {'fragile': FRAGILE, 'bridge_open': BRIDGE}.get(kind, CONCRETE), rect)
    pygame.draw.rect(surf, CONCRETE_LINE, rect, 1)
    hi = pygame.Surface((rect.w, max(2, rect.h // 10)), pygame.SRCALPHA)   # bevel: lit top edge
    hi.fill((255, 255, 255, 40))
    surf.blit(hi, rect.topleft)
    cx, cy, r = rect.centerx, rect.centery, rect.width // 3
    if kind == 'goal':                                   # stairs down to the next floor, RPG style
        steps = 5
        well = rect.inflate(-max(4, rect.w // 8), -max(4, rect.h // 10))
        for i in range(steps):                           # each step lower and darker than the one above
            k = i / (steps - 1)
            y0 = well.y + well.h * i // steps
            step = pygame.Rect(well.x, y0, well.w, well.h // steps + 1)
            pygame.draw.rect(surf, tuple(int(a + (b - a) * k) for a, b in zip((196, 184, 162), (34, 30, 30))), step)
            pygame.draw.line(surf, tuple(int(c * (1 - 0.6 * k)) for c in (240, 230, 210)), step.topleft, step.topright, 2)
        rail = max(3, rect.w // 12)
        for x in (well.x - rail, well.right):            # side walls of the stairwell
            pygame.draw.rect(surf, (88, 74, 60), (x, well.y, rail, well.h))
        pygame.draw.rect(surf, (60, 50, 42), well.inflate(2 * rail, 2), 2)
    elif kind == 'fragile':
        pygame.draw.lines(surf, CONCRETE_SIDE, False, [(rect.x + 6, rect.y + 8), (cx, cy), (rect.right - 8, cy + 6)], 2)
    elif kind == 'soft':
        pygame.draw.circle(surf, SOFT, rect.center, r)
    elif kind == 'heavy':
        pygame.draw.line(surf, HEAVY, (cx - r, cy - r), (cx + r, cy + r), 4)
        pygame.draw.line(surf, HEAVY, (cx - r, cy + r), (cx + r, cy - r), 4)
    elif kind == 'split':
        pygame.draw.arc(surf, SPLIT, rect.inflate(-6, -6), 2.2, 4.1, 4)
        pygame.draw.arc(surf, SPLIT, rect.inflate(-6, -6), -0.95, 0.95, 4)
    elif kind == 'bridge_open':
        for k in (-r, 0, r):
            pygame.draw.line(surf, CONCRETE_SIDE, (rect.x + 4, cy + k), (rect.right - 4, cy + k), 1)


def block(surf, rect, active=True):
    """Metallic block over ``rect`` (bounding box of its cells), with a drop shadow."""
    shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 70), shadow.get_rect(), border_radius=8)
    surf.blit(shadow, (rect.x + 5, rect.y + 7))
    body = rect.inflate(-6, -6)
    pygame.draw.rect(surf, BLOCK_DARK, body.move(0, 3), border_radius=8)
    pygame.draw.rect(surf, BLOCK, body, border_radius=8)
    pygame.draw.rect(surf, BLOCK_LIGHT, body.inflate(-body.width // 3, -body.height // 2).move(0, -body.height // 6),
                     border_radius=6)
    pygame.draw.rect(surf, BLOCK_LIGHT if active else BLOCK_DARK, body, 2 if active else 1, border_radius=8)
    if active and rect.width < 60:
        pygame.draw.rect(surf, HINT, rect, 2, border_radius=8)   # ring marks the controlled cube
