"""The building around a floor, drawn once into the floor's background.

Top floor: the open roof (gravel, parapet, rooftop equipment, antenna) above the tower's facade.
Lower floors: closed rooms in the style of top-down RPG interiors: dark outside, a tall back wall
with things hung on it, wall caps on the other sides, and furniture laid out the way offices are:
storage and desks against the walls, desk pairs and meeting tables in the middle, the path kept clear.
"""
import math
import random

import pygame

from . import sprites

MX, MY = 3, 2                                # tiles of building left/right and above/below the playfield
ROOF, ROOF_DOT, PARAPET = (98, 94, 90), (120, 116, 110), (176, 170, 160)
WOOD, WOOD_LINE = (104, 90, 76), (92, 79, 66)
WALL, MULLION, WINDOW, LIT = (118, 112, 106), (92, 88, 84), (64, 92, 132), (255, 206, 120)


def _shadow(surf, rect, k=0.18):
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (0, 0, 0, 70), layer.get_rect(), border_radius=max(2, rect.w // 8))
    surf.blit(layer, (rect.x + int(rect.w * k * 0.5) + 2, rect.y - int(rect.h * k * 0.3) + 2))


def _sprite(surf, name, rect, angle=0):
    """Draw the generated sprite for a prop with a soft shadow, rotated by angle (0/90/180/270,
    counter-clockwise, so 90 puts the sprite's top edge on the left). False if there is no sprite."""
    side = angle % 180 == 90
    img = sprites.prop(name, rect.h, rect.w) if side else sprites.prop(name, rect.w, rect.h)
    if img is None:
        return False
    if angle:
        img = pygame.transform.rotate(img, angle)
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
         'skylight': (1.2, 1.2), 'desk': (1.4, 1.2), 'plant': (0.6, 0.6), 'sofa': (1.8, 0.7),
         'cabinet': (1, 1), 'shelf': (2, 1), 'printer': (1, 1), 'cooler': (1, 1), 'boxes': (1, 1),
         'meeting': (2, 2), 'crate': (1, 1), 'duct': (2, 1), 'hvac': (1, 1)}   # in tiles


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
    elif kind == 'cabinet':                                  # filing cabinet, drawers seen from above
        pygame.draw.rect(surf, (130, 136, 146), r, border_radius=3)
        pygame.draw.rect(surf, (100, 106, 116), r.inflate(-r.w // 5, -r.h // 5), 2, border_radius=2)
        pygame.draw.line(surf, (90, 96, 106), (r.x + r.w // 4, r.bottom - r.h // 6), (r.right - r.w // 4, r.bottom - r.h // 6), 3)
    elif kind == 'shelf':                                    # bookshelf full of coloured books
        pygame.draw.rect(surf, (120, 90, 62), r)
        x, i = r.x + r.w // 20, 0
        while x < r.right - r.w // 20:
            bw = max(2, r.w // 18 + (i * 7) % 5)
            col = ((170, 60, 50), (60, 90, 150), (210, 170, 70), (70, 120, 80), (220, 220, 210))[i % 5]
            pygame.draw.rect(surf, col, (x, r.y + r.h // 6, bw, r.h * 2 // 3))
            x, i = x + bw + 1, i + 1
    elif kind == 'printer':
        pygame.draw.rect(surf, (220, 222, 226), r.inflate(-r.w // 8, -r.h // 6), border_radius=4)
        pygame.draw.rect(surf, (60, 64, 72), r.inflate(-r.w // 3, -r.h * 2 // 3).move(0, -r.h // 6))
        pygame.draw.rect(surf, (250, 250, 250), r.inflate(-r.w // 2, -r.h * 3 // 4).move(0, r.h // 5))
    elif kind == 'cooler':                                   # water cooler: bottle on a stand
        pygame.draw.rect(surf, (230, 232, 236), r.inflate(-r.w // 4, -r.h // 4), border_radius=6)
        pygame.draw.circle(surf, (120, 180, 230), r.center, r.w // 4)
        pygame.draw.circle(surf, (180, 220, 250), r.center, r.w // 8)
    elif kind == 'boxes':                                    # stacked cardboard boxes
        for dx, dy, k in ((-0.15, -0.1, 0.55), (0.18, 0.15, 0.5), (-0.1, 0.22, 0.4)):
            bx = pygame.Rect(0, 0, int(r.w * k), int(r.h * k))
            bx.center = (int(r.centerx + dx * r.w), int(r.centery + dy * r.h))
            pygame.draw.rect(surf, (196, 150, 98), bx)
            pygame.draw.line(surf, (160, 118, 72), bx.midtop, bx.midbottom, 2)
            pygame.draw.rect(surf, (150, 110, 66), bx, 1)
    elif kind == 'meeting':                                  # round meeting table with chairs
        for a in range(6):
            ang = a * math.pi / 3
            c = (int(r.centerx + math.cos(ang) * r.w * 0.38), int(r.centery + math.sin(ang) * r.h * 0.38))
            pygame.draw.circle(surf, (60, 64, 76), c, r.w // 10)
        pygame.draw.circle(surf, (200, 176, 140), r.center, int(r.w * 0.3))
        pygame.draw.circle(surf, (170, 146, 110), r.center, int(r.w * 0.3), 2)
    elif kind == 'crate':                                    # wooden crate on the roof
        pygame.draw.rect(surf, (168, 128, 82), r.inflate(-r.w // 8, -r.h // 8))
        inner = r.inflate(-r.w // 8, -r.h // 8)
        pygame.draw.line(surf, (120, 88, 52), inner.topleft, inner.bottomright, 3)
        pygame.draw.line(surf, (120, 88, 52), inner.topright, inner.bottomleft, 3)
        pygame.draw.rect(surf, (120, 88, 52), inner, 3)
    elif kind == 'duct':                                     # HVAC duct run
        pygame.draw.rect(surf, (176, 180, 186), r.inflate(0, -r.h // 3), border_radius=3)
        for i in range(1, 4):
            x = r.x + r.w * i // 4
            pygame.draw.line(surf, (140, 144, 150), (x, r.y + r.h // 6), (x, r.bottom - r.h // 6), 2)
    elif kind == 'hvac':                                     # small rooftop unit with a grille
        pygame.draw.rect(surf, (160, 166, 172), r.inflate(-r.w // 8, -r.h // 8), border_radius=3)
        g = r.inflate(-r.w // 3, -r.h // 3)
        for y in range(g.y, g.bottom, max(3, g.h // 6)):
            pygame.draw.line(surf, (110, 114, 120), (g.x, y), (g.right, y), 2)


# Props that fill every cell the block cannot use, so the playfield reads as a path through a real room.
GRID_PROPS = {
    'roof': {'big': [('tank', 2, 2), ('ac', 2, 1), ('solar', 2, 1), ('duct', 2, 1)],
             'small': ['hvac', 'crate', 'vent', 'skylight', 'vent']},
    'office': {'big': [('meeting', 2, 2), ('shelf', 2, 1), ('sofa', 2, 1)],
               'small': ['desk', 'desk', 'cabinet', 'printer', 'cooler', 'boxes', 'plant', 'plant']},
}


def _antenna(surf, r, sq):
    base = r.center
    top = (base[0], base[1] - int(sq * 2.4))
    pygame.draw.line(surf, (60, 60, 66), base, top, 3)
    for i in (0.35, 0.65):
        y = int(base[1] + (top[1] - base[1]) * i)
        pygame.draw.line(surf, (60, 60, 66), (base[0] - 8, y), (base[0] + 8, y), 2)
    return top


def _furnish(surf, game, rng, roof, fp):
    """Fill the floor around the path: every blocked cell next to the path gets an object, the rest a few."""
    fx0, fy0, fx1, fy1 = fp
    walk = set(game.level.kinds)                                  # path cells, bridges included
    free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
    near = {(x, y) for x, y in free if any((x + dx, y + dy) in walk for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
    props = GRID_PROPS['roof' if roof else 'office']
    beacon = None
    if roof and free - near:
        spot = rng.choice(sorted(free - near))
        free.discard(spot)
        beacon = _antenna(surf, _rect(game, *spot), game.square_size)
    for x, y in sorted(free, key=lambda c: (c not in near, rng.random())):
        if (x, y) not in free:
            continue
        if rng.random() < (0.5 if (x, y) in near else 0.3):
            kind, w, h = rng.choice(props['big'])
            turned = w != h and rng.random() < 0.5
            if turned:
                w, h = h, w
            cells = {(x + i, y + j) for i in range(w) for j in range(h)}
            if cells <= free:
                free -= cells
                _put(surf, kind, _rect(game, x, y, w, h), 90 if turned else 0)
                continue
        if (x, y) in near or rng.random() < 0.15:
            free.discard((x, y))
            _put(surf, rng.choice(props['small']), _rect(game, x, y))
    return beacon


FILL = {'vent': 0.55, 'plant': 0.8, 'cooler': 0.8, 'boxes': 0.85, 'hvac': 0.85, 'crate': 0.85}   # share of the cell


def _rug(surf, rect):
    pygame.draw.rect(surf, (128, 52, 52), rect, border_radius=6)
    pygame.draw.rect(surf, (196, 150, 90), rect.inflate(-rect.w // 10, -rect.h // 10), 3, border_radius=4)
    pygame.draw.rect(surf, (150, 70, 66), rect.inflate(-rect.w // 4, -rect.h // 4), 2, border_radius=3)


def _furnish_office(surf, game, rng, fp):
    """Office layout: aisle (the path) kept clear; along the walls storage and desks facing the wall,
    in the middle back-to-back desk pairs and meeting tables on rugs; loose cells by the path get plants,
    boxes or cabinets."""
    fx0, fy0, fx1, fy1 = fp
    top = fy0 + 1                                                 # row fy0 is the back wall
    walk = set(game.level.kinds)
    free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(top, fy1 + 1)} - walk
    near = {(x, y) for x, y in free if any((x + dx, y + dy) in walk for dx in (-1, 0, 1) for dy in (-1, 0, 1))}

    def take(kind, x, y, w=1, h=1, angle=0):
        free.difference_update((x + i, y + j) for i in range(w) for j in range(h))
        _put(surf, kind, _rect(game, x, y, w, h), angle)

    x = fx0                                                       # back wall: shelves and storage
    while x <= fx1:
        if (x, top) in free:
            if (x + 1, top) in free and rng.random() < 0.5:
                take('shelf', x, top, 2, 1)
                x += 2
                continue
            take(rng.choice(['cabinet', 'printer', 'cooler', 'desk', 'plant']), x, top)
        x += 1
    for x in range(fx0, fx1 + 1):                                 # front wall: desks facing it
        if (x, fy1) in free:
            take('desk' if rng.random() < 0.7 else 'plant', x, fy1, angle=180)
    for y in range(top + 1, fy1):                                 # side walls: desks facing them
        for x, angle in ((fx0, 90), (fx1, 270)):
            if (x, y) in free:
                take('desk' if rng.random() < 0.6 else rng.choice(['cabinet', 'plant']), x, y, angle=angle)

    meetings = 0
    for x, y in sorted(free, key=lambda c: rng.random()):         # middle: meeting tables on rugs, desk pairs
        if (x, y) not in free:
            continue
        block = {(x + i, y + j) for i in range(2) for j in range(2)}
        if block <= free and meetings < 2 and rng.random() < 0.5:   # one or two meeting corners per floor
            meetings += 1
            _rug(surf, _rect(game, x - 0.1, y - 0.1, 2.2, 2.2))
            take('meeting', x, y, 2, 2)
        elif (x, y + 1) in free and rng.random() < 0.6:
            take('desk', x, y, angle=180)                         # back to back, chairs outwards
            take('desk', x, y + 1)
        elif (x, y) in near or rng.random() < 0.2:
            take(rng.choice(['plant', 'boxes', 'cabinet', 'cooler', 'plant']), x, y)


def _office_shell(surf, game, fp, rng):
    """Walls: a tall back wall with things on it, thin wall caps elsewhere, soft shade along the walls."""
    fx0, fy0, fx1, fy1 = fp
    sq = game.square_size
    room = _rect(game, fx0, fy0, fx1 - fx0 + 1, fy1 - fy0 + 1)
    cap = max(4, int(sq * 0.22))
    face = _rect(game, fx0, fy0, fx1 - fx0 + 1, 1)
    pygame.draw.rect(surf, (222, 210, 186), face)                                  # painted wall
    pygame.draw.rect(surf, (238, 228, 206), (face.x, face.y, face.w, face.h // 3))  # lighter upper band
    pygame.draw.rect(surf, (110, 82, 58), (face.x, face.bottom - face.h // 7, face.w, face.h // 7))   # skirting
    x = fx0 + 1
    while x < fx1:                                                # things hung on the back wall
        kind = rng.choice(['board', 'clock', 'frame', 'frame', 'notice', None])
        r = _rect(game, x, fy0)
        if kind == 'board' and x + 1 < fx1:
            wb = _rect(game, x + 0.15, fy0 + 0.15, 1.7, 0.55)
            pygame.draw.rect(surf, (248, 248, 250), wb)
            pygame.draw.rect(surf, (150, 150, 160), wb, 2)
            for i in range(3):
                y = wb.y + wb.h * (i + 1) // 4
                pygame.draw.line(surf, ((60, 90, 170), (190, 60, 60), (60, 140, 90))[i], (wb.x + 6, y), (wb.x + wb.w // (2 + i), y), 2)
            x += 2
            continue
        if kind == 'clock':
            pygame.draw.circle(surf, (250, 250, 250), (r.centerx, r.y + r.h * 2 // 5), r.w // 5)
            pygame.draw.circle(surf, (60, 60, 66), (r.centerx, r.y + r.h * 2 // 5), r.w // 5, 2)
            c = (r.centerx, r.y + r.h * 2 // 5)
            pygame.draw.line(surf, (40, 40, 44), c, (c[0], c[1] - r.w // 7), 2)
            pygame.draw.line(surf, (40, 40, 44), c, (c[0] + r.w // 9, c[1]), 2)
        elif kind == 'frame':
            fr = _rect(game, x + 0.22, fy0 + 0.15, 0.56, 0.45)
            pygame.draw.rect(surf, (90, 66, 44), fr)
            pygame.draw.rect(surf, rng.choice([(110, 160, 190), (200, 150, 90), (120, 170, 110)]), fr.inflate(-6, -6))
        elif kind == 'notice':
            nb = _rect(game, x + 0.15, fy0 + 0.15, 0.7, 0.5)
            pygame.draw.rect(surf, (176, 132, 88), nb)
            for _ in range(4):
                pygame.draw.rect(surf, rng.choice([(250, 240, 160), (250, 250, 250), (180, 220, 250)]),
                                 (rng.randrange(nb.x + 3, nb.right - 10), rng.randrange(nb.y + 3, nb.bottom - 10), 8, 8))
        x += 1
    shade = pygame.Surface((room.w, sq // 2), pygame.SRCALPHA)    # contact shadow under the back wall
    for i in range(shade.get_height()):
        shade.fill((0, 0, 0, max(0, 70 - i * 140 // sq)), (0, i, room.w, 1))
    surf.blit(shade, (room.x, face.bottom))
    wall = (58, 54, 62)
    pygame.draw.rect(surf, wall, (room.x - cap, room.y - cap, room.w + 2 * cap, cap))      # top cap
    pygame.draw.rect(surf, wall, (room.x - cap, room.y - cap, cap, room.h + 2 * cap))      # left
    pygame.draw.rect(surf, wall, (room.right, room.y - cap, cap, room.h + 2 * cap))        # right
    pygame.draw.rect(surf, wall, (room.x - cap, room.bottom, room.w + 2 * cap, cap))       # bottom
    pygame.draw.rect(surf, (96, 92, 102), room.inflate(2 * cap, 2 * cap), 2)


def _put(surf, kind, rect, angle=0):
    k = FILL.get(kind, 0.93)
    r = pygame.Rect(0, 0, int(rect.w * k), int(rect.h * k))
    r.center = rect.center
    if not _sprite(surf, kind, r, angle):
        draw_code_prop(surf, kind, r)


def bake(background, game, floor, count):
    """Draw the building into ``background`` (in place). Returns the roof beacon's screen position or None."""
    rng = random.Random(1000 + game.level.level)
    fx0, fy0, fx1, fy1, _ = _footprint(game)
    roof = floor == 0

    if roof:
        _facade(background, game, fx0, fx1, fy1, floor, count, rng)
    else:
        background.fill((8, 8, 12))                               # a closed room: nothing outside
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
    if roof:
        beacon = _furnish(background, game, rng, True, (fx0, fy0, fx1, fy1))
    else:
        beacon = None
        _furnish_office(background, game, rng, (fx0, fy0, fx1, fy1))
        _office_shell(background, game, (fx0, fy0, fx1, fy1), rng)

    if roof:                                                     # parapet with its front face
        edge = max(4, int(sq * 0.2))
        pygame.draw.rect(background, PARAPET, slab, edge)
        pygame.draw.rect(background, (140, 134, 126), (slab.x, slab.bottom, slab.w, edge))
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
