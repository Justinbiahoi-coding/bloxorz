"""Rooftop look: procedural sky, concrete tiles with an edge, metallic block. No image assets."""
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


def tile(surf, rect, kind, edge_below):
    """One floor tile. ``edge_below``: the tile under it is void, so show the slab's side face."""
    depth = max(4, rect.height // 4)
    if edge_below:
        pygame.draw.rect(surf, CONCRETE_SIDE, (rect.x, rect.bottom, rect.width, depth))
    pygame.draw.rect(surf, CONCRETE, rect)
    pygame.draw.rect(surf, CONCRETE_LINE, rect, 1)
    if kind == 'goal':
        pygame.draw.rect(surf, PIT, rect.inflate(-rect.width // 3, -rect.height // 3), border_radius=4)
        pygame.draw.circle(surf, RING, rect.center, rect.width * 2 // 5, 2)


def block(surf, rect):
    """Metallic block over ``rect`` (bounding box of its cells), with a drop shadow."""
    shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 70), shadow.get_rect(), border_radius=8)
    surf.blit(shadow, (rect.x + 5, rect.y + 7))
    body = rect.inflate(-6, -6)
    pygame.draw.rect(surf, BLOCK_DARK, body.move(0, 3), border_radius=8)
    pygame.draw.rect(surf, BLOCK, body, border_radius=8)
    pygame.draw.rect(surf, BLOCK_LIGHT, body.inflate(-body.width // 3, -body.height // 2).move(0, -body.height // 6),
                     border_radius=6)
    pygame.draw.rect(surf, BLOCK_LIGHT, body, 2, border_radius=8)
