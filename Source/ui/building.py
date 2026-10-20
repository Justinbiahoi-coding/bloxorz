"""The skyscraper around a floor, drawn once into the floor's background.

Top floor: a roof (gravel, parapet, AC units, water tank, vents, solar panels, antenna).
Lower floors: an office cut-away (wood floor, glass curtain wall, desks, plants, columns).
Every floor also shows the building's south facade dropping to the bottom of the screen,
and the empty cells of the playfield as dark shafts with the floor below faintly visible.
"""
import math
import random

import pygame

from . import sprites

MX, MY = 3, 2                                # tiles of building left/right and above/below the playfield
ROOF, ROOF_DOT, PARAPET = (98, 94, 90), (120, 116, 110), (176, 170, 160)
WOOD, WOOD_LINE, GLASS = (104, 90, 76), (92, 79, 66), (170, 210, 235)
WALL, MULLION, WINDOW, LIT = (118, 112, 106), (92, 88, 84), (64, 92, 132), (255, 206, 120)
SHAFT, SHAFT_GRID = (16, 18, 28), (30, 34, 48)


def _shadow(surf, rect, k=0.18):
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (0, 0, 0, 70), layer.get_rect(), border_radius=max(2, rect.w // 8))
    surf.blit(layer, (rect.x + int(rect.w * k * 0.5) + 2, rect.y - int(rect.h * k * 0.3) + 2))


def _sprite(surf, name, rect):
    """Draw the generated sprite for a prop (with a soft shadow); False if there is none."""
    img = sprites.prop(name, rect.w, rect.h)
    if img is None:
        return False
    pos = img.get_rect(center=rect.center)
    shadow = pygame.mask.from_surface(img).to_surface(setcolor=(0, 0, 0, 80), unsetcolor=(0, 0, 0, 0))
    surf.blit(shadow, (pos.x + max(2, rect.w // 14), pos.y + max(2, rect.h // 14)))
    surf.blit(img, pos)
    return True


def _footprint(game):
    xs = [x for x, _ in game.level.kinds]
    ys = [y for _, y in game.level.kinds]
    return min(xs) - MX, min(ys) - MY, max(xs) + MX, max(ys) + MY, (min(xs), min(ys), max(xs), max(ys))


def _rect(game, x, y, w=1.0, h=1.0):
    sq = game.square_size
    return pygame.Rect(int(game.starting_x + x * sq), int(game.starting_y + y * sq), int(w * sq), int(h * sq))


def _facade(surf, game, fx0, fx1, fy1, floor, count, rng):
    """South face of the tower, from the footprint's edge down past the bottom of the screen."""
    sq = game.square_size
    top = _rect(game, fx0, fy1 + 1).y
    left, right = _rect(game, fx0, 0).x, _rect(game, fx1 + 1, 0).x
    if top >= surf.get_height():
        return
    pygame.draw.rect(surf, WALL, (left, top, right - left, surf.get_height() - top))
    band = max(10, int(sq * 0.8))
    lit_share = 0.12 + 0.55 * floor / max(1, count - 1)     # more lights on as it gets darker outside
    y = top + band // 4
    while y < surf.get_height():
        x = left
        while x < right - 4:
            win = pygame.Rect(x + sq // 6, y, max(4, sq - sq // 3), max(4, band - band // 3))
            color = LIT if rng.random() < lit_share else WINDOW
            pygame.draw.rect(surf, color, win)
            if color == WINDOW:                              # sky reflection on dark glass
                pygame.draw.line(surf, (110, 140, 180), win.topleft, (win.x + win.w // 2, win.bottom), 2)
            x += sq
        pygame.draw.line(surf, MULLION, (left, y + band - band // 6), (right, y + band - band // 6), 2)
        y += band
    for x in range(left, right + 1, sq):                     # pilasters
        pygame.draw.line(surf, MULLION, (x, top), (x, surf.get_height()), 3)
    shade = pygame.Surface((right - left, surf.get_height() - top), pygame.SRCALPHA)
    for i in range(shade.get_height()):                      # fades towards the street
        shade.fill((10, 12, 24, min(150, i // 3)), (0, i, shade.get_width(), 1))
    surf.blit(shade, (left, top))


SIZES = {'tank': (1.6, 1.6), 'antenna': (0.6, 0.6), 'ac': (1.6, 1.1), 'solar': (2.2, 1.0), 'vent': (0.5, 0.5),
         'skylight': (1.2, 1.2), 'desk': (1.4, 1.2), 'plant': (0.6, 0.6), 'sofa': (1.8, 0.7)}   # in tiles


def draw_code_prop(surf, kind, r, shadow=True):
    """The code-drawn version of a prop inside rect r (also the sketch that tools/make_sketches.py feeds to SDXL)."""
    if shadow and kind not in ('vent', 'plant'):
        _shadow(surf, r)
    if kind == 'tank':
        pygame.draw.ellipse(surf, (150, 150, 158), r)
        for k in (0.8, 0.55):
            pygame.draw.ellipse(surf, (120, 120, 130), r.inflate(-r.w * (1 - k), -r.h * (1 - k)), 2)
        pygame.draw.ellipse(surf, (200, 200, 208), r.inflate(-r.w * 0.75, -r.h * 0.75))
    elif kind == 'ac':
        pygame.draw.rect(surf, (186, 186, 190), r, border_radius=4)
        fan = r.h * 0.36
        for cx in (r.x + r.w * 0.3, r.x + r.w * 0.7):
            pygame.draw.circle(surf, (90, 92, 98), (int(cx), r.centery), int(fan))
            pygame.draw.circle(surf, (140, 142, 148), (int(cx), r.centery), int(fan * 0.35))
        pygame.draw.rect(surf, (130, 130, 136), r, 2, border_radius=4)
    elif kind == 'solar':
        pygame.draw.rect(surf, (36, 56, 104), r)
        for i in range(1, 6):
            pygame.draw.line(surf, (90, 120, 170), (r.x + r.w * i // 6, r.y), (r.x + r.w * i // 6, r.bottom))
        pygame.draw.line(surf, (90, 120, 170), (r.x, r.centery), (r.right, r.centery))
        pygame.draw.rect(surf, (170, 176, 186), r, 2)
    elif kind == 'vent':
        pygame.draw.circle(surf, (70, 70, 76), r.center, r.w // 2)
        pygame.draw.circle(surf, (150, 150, 156), r.center, r.w // 2, 2)
    elif kind == 'skylight':
        pygame.draw.rect(surf, (120, 170, 210), r)
        pygame.draw.line(surf, (220, 240, 255), (r.x + 3, r.bottom - 4), (r.right - 4, r.y + 3), 3)
        pygame.draw.rect(surf, PARAPET, r, 3)
    elif kind == 'desk':
        pygame.draw.rect(surf, (196, 170, 132), r, border_radius=3)
        mon = pygame.Rect(0, 0, r.w // 3, max(3, r.h // 6))
        mon.midtop = (r.centerx, r.y + r.h // 6)
        pygame.draw.rect(surf, (40, 44, 54), mon)
        pygame.draw.circle(surf, (60, 64, 76), (r.centerx, r.bottom + r.h // 4), r.h // 4)   # chair
    elif kind == 'plant':
        pygame.draw.circle(surf, (120, 86, 60), r.center, r.w // 3)
        for a in range(6):
            ang = a * math.pi / 3
            c = (int(r.centerx + math.cos(ang) * r.w * 0.25), int(r.centery + math.sin(ang) * r.w * 0.25))
            pygame.draw.circle(surf, (70, 140, 80), c, r.w // 4)
    elif kind == 'sofa':
        pygame.draw.rect(surf, (150, 70, 70), r, border_radius=6)
        pygame.draw.rect(surf, (120, 54, 54), r.inflate(-r.w // 6, -r.h // 3).move(0, r.h // 8), border_radius=4)


def _place(surf, game, slots, rng, placed, kinds):
    """Place props of the given kinds on free building cells; returns the antenna top, if one was placed."""
    beacon = None
    for kind in kinds:
        w, h = SIZES[kind]
        spot = _find_spot(slots, placed, w, h, rng)
        if spot is None:
            continue
        placed.append((*spot, w, h))
        r = _rect(game, *spot, w, h)
        if kind == 'antenna':
            base = r.center
            top = (base[0], base[1] - int(game.square_size * 2.4))
            pygame.draw.line(surf, (60, 60, 66), base, top, 3)
            for i in (0.35, 0.65):
                y = int(base[1] + (top[1] - base[1]) * i)
                pygame.draw.line(surf, (60, 60, 66), (base[0] - 8, y), (base[0] + 8, y), 2)
            beacon = top
        elif not _sprite(surf, kind, r):
            draw_code_prop(surf, kind, r)
    return beacon


def _roof_props(surf, game, slots, rng, board):
    kinds = ['tank', 'antenna'] + ['ac'] * 3 + ['solar'] * 2 + ['vent'] * 5 + ['skylight']
    return _place(surf, game, slots, rng, [board], kinds)


def _office_props(surf, game, slots, rng, fp, board):
    fx0, fy0, fx1, fy1 = fp
    for x in range(fx0 + 1, fx1 + 1, 4):                     # structural columns along the walls
        for y in (fy0 + 0.25, fy1 + 0.25):
            if all((int(x + dx), int(y + dy)) in slots for dx in (0, 0.4) for dy in (0, 0.4)):
                r = _rect(game, x, y, 0.5, 0.5)
                _shadow(surf, r)
                pygame.draw.rect(surf, (150, 144, 136), r)
    _place(surf, game, slots, rng, [board], ['desk'] * 6 + ['plant'] * 5 + ['sofa'] * 2)


def _find_spot(slots, placed, w, h, rng, tries=60):
    """A position (on a half-cell grid) whose whole w x h area lies in ``slots`` and overlaps nothing placed."""
    cells = sorted(slots)
    for _ in range(tries):
        cx, cy = rng.choice(cells)
        x, y = cx + rng.choice((0, 0.5)) - (w > 1) * 0.5, cy + rng.choice((0, 0.5))
        covered = {(int(math.floor(x + dx)), int(math.floor(y + dy)))
                   for dx in (0, w * 0.5, w - 0.01) for dy in (0, h * 0.5, h - 0.01)}
        if not covered <= slots:
            continue
        if any(x < px + pw + 0.2 and px < x + w + 0.2 and y < py + ph + 0.2 and py < y + h + 0.2
               for px, py, pw, ph in placed):
            continue
        return x, y
    return None


def bake(background, game, floor, count):
    """Draw the building into ``background`` (in place). Returns the roof beacon's screen position or None."""
    rng = random.Random(1000 + game.level.level)
    fx0, fy0, fx1, fy1, (bx0, by0, bx1, by1) = _footprint(game)
    roof = floor == 0

    _facade(background, game, fx0, fx1, fy1, floor, count, rng)
    slab = _rect(game, fx0, fy0, fx1 - fx0 + 1, fy1 - fy0 + 1)
    textured = sprites.fill(background, slab, 'gravel' if roof else 'wood', int(game.square_size))
    if textured:                                                 # calm the texture so the playfield stays the focus
        veil = pygame.Surface(slab.size, pygame.SRCALPHA)
        veil.fill((*(ROOF if roof else WOOD), 130 if roof else 60))
        background.blit(veil, slab.topleft)
    if not textured:                                             # code-drawn fallback
        pygame.draw.rect(background, ROOF if roof else WOOD, slab)
        if roof:
            for _ in range(slab.w * slab.h // 90):               # gravel
                pygame.draw.circle(background, ROOF_DOT if rng.random() < 0.6 else (84, 80, 76),
                                   (rng.randrange(slab.x, slab.right), rng.randrange(slab.y, slab.bottom)), 1)
        else:
            for y in range(slab.y, slab.bottom, max(4, game.square_size // 2)):   # floor planks
                pygame.draw.line(background, WOOD_LINE, (slab.x, y), (slab.right, y), 1)

    sq = game.square_size
    for y in range(by0, by1 + 1):                                # shafts where the playfield has no tile
        for x in range(bx0, bx1 + 1):
            kind = game.level.kinds.get((x, y))
            if kind is None or kind in 'lrkq':
                r = _rect(game, x, y)
                pygame.draw.rect(background, SHAFT, r)
                pygame.draw.rect(background, SHAFT_GRID, r.move(0, sq // 3).clip(r), 1)

    slots = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)
             if not (bx0 <= x <= bx1 and by0 <= y <= by1)}
    board = (bx0, by0, bx1 - bx0 + 1, by1 - by0 + 1)        # props keep a gap from the playfield
    beacon = _roof_props(background, game, slots, rng, board) if roof else None
    if not roof:
        _office_props(background, game, slots, rng, (fx0, fy0, fx1, fy1), board)

    edge = max(4, int(sq * 0.2))
    if roof:                                                     # parapet with its front face
        pygame.draw.rect(background, PARAPET, slab, edge)
        pygame.draw.rect(background, (140, 134, 126), (slab.x, slab.bottom, slab.w, edge))
    else:                                                        # glass curtain wall
        pygame.draw.rect(background, GLASS, slab, max(3, edge // 2))
        for x in range(slab.x, slab.right, sq):
            pygame.draw.line(background, (120, 150, 170), (x, slab.y), (x, slab.y + edge), 2)
    return beacon


def draw_beacon(surf, pos, now):
    """Blinking red aircraft light on top of the antenna."""
    if pos is None:
        return
    a = int(128 + 127 * math.sin(now / 260))
    glow = pygame.Surface((28, 28), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 60, 50, a // 3), (14, 14), 13)
    pygame.draw.circle(glow, (255, 80, 70, a), (14, 14), 5)
    surf.blit(glow, (pos[0] - 14, pos[1] - 14))
