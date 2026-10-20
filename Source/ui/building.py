"""The building around a floor, drawn once into the floor's background.

Top floor: the open roof (gravel, parapet, rooftop equipment, antenna) above the tower's facade.
Lower floors: rooms seen through an opening in the ceiling of the floor above (ceiling tiles,
panel lights, vents), with a few furniture groups laid out like a normal office and the path kept clear.
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
    """A normal office, not a warehouse: a few groups with breathing room between them.
    Gaps inside the playfield get a group (desk pair, meeting table on a rug, plant) so it is clear why the
    block cannot go there; along the walls only a handful of pieces, spaced out; the aisle stays clear."""
    fx0, fy0, fx1, fy1 = fp
    walk = set(game.level.kinds)
    xs, ys = [x for x, _ in walk], [y for _, y in walk]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    free = {(x, y) for x in range(fx0, fx1 + 1) for y in range(fy0, fy1 + 1)} - walk
    used = set()

    def room_for(cells):                       # cells free, and an empty cell between this and other furniture
        return cells <= free and not any((x + dx, y + dy) in used for x, y in cells
                                         for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def take(kind, x, y, w=1, h=1, angle=0):
        cells = {(x + i, y + j) for i in range(w) for j in range(h)}
        used.update(cells)
        free.difference_update(cells)
        _put(surf, kind, _rect(game, x, y, w, h), angle)

    inside = sorted((c for c in free if bx0 <= c[0] <= bx1 and by0 <= c[1] <= by1), key=lambda c: rng.random())
    meetings = 0
    for x, y in inside:                        # gaps in the playfield
        block = {(x + i, y + j) for i in range(2) for j in range(2)}
        pair = {(x, y), (x, y + 1)}
        if meetings < 1 and room_for(block):
            meetings += 1
            _rug(surf, _rect(game, x - 0.1, y - 0.1, 2.2, 2.2))
            take('meeting', x, y, 2, 2)
        elif pair <= free and rng.random() < 0.5:
            take('desk', x, y, angle=180)       # back to back
            take('desk', x, y + 1)
        elif (x, y) in free and rng.random() < 0.45:
            take(rng.choice(['plant', 'plant', 'cabinet', 'cooler']), x, y)

    for x in range(fx0 + 1, fx1, 3):           # along the back wall: storage, spaced out
        if room_for({(x, fy0), (x + 1, fy0)}) and rng.random() < 0.6:
            take('shelf', x, fy0, 2, 1)
        elif room_for({(x, fy0)}) and rng.random() < 0.5:
            take(rng.choice(['printer', 'cooler', 'cabinet']), x, fy0)
    for x in range(fx0 + 1, fx1, 2):           # front wall: a few desks facing the window
        if room_for({(x, fy1)}) and rng.random() < 0.45:
            take('desk', x, fy1, angle=180)
    for y in range(fy0 + 2, fy1 - 1, 2):       # side walls
        for x, angle in ((fx0, 90), (fx1, 270)):
            if room_for({(x, y)}) and rng.random() < 0.4:
                take(rng.choice(['desk', 'desk', 'cabinet']), x, y, angle=angle)
    for corner in ((fx0, fy0), (fx1, fy0), (fx0, fy1), (fx1, fy1)):   # plants in the corners
        if room_for({corner}):
            take('plant', *corner)


def _ceiling(surf, game, fp, rng):
    """The floor above, seen from below around the opening: ceiling tiles, panel lights, vents,
    sprinklers; then the cut slab edge, the shadow it throws into the room and the window line."""
    fx0, fy0, fx1, fy1 = fp
    sq = game.square_size
    w, h = surf.get_size()
    room = _rect(game, fx0, fy0, fx1 - fx0 + 1, fy1 - fy0 + 1)
    ceiling = pygame.Surface((w, h))
    ceiling.fill((222, 220, 214))
    panel = max(8, sq // 2)
    ox, oy = room.x % panel, room.y % panel                      # grid lines up with the room
    for x in range(ox - panel, w, panel):
        pygame.draw.line(ceiling, (200, 196, 190), (x, 0), (x, h), 1)
    for y in range(oy - panel, h, panel):
        pygame.draw.line(ceiling, (200, 196, 190), (0, y), (w, y), 1)
    for gy, y in enumerate(range(oy - panel, h, panel)):
        for gx, x in enumerate(range(ox - panel, w, panel)):
            cell = pygame.Rect(x + 1, y + 1, panel - 1, panel - 1)
            if gx % 4 == 1 and gy % 4 == 1:                      # LED panel light with a soft halo
                halo = pygame.Surface((panel * 3, panel * 3), pygame.SRCALPHA)
                pygame.draw.ellipse(halo, (255, 250, 225, 40), halo.get_rect())
                ceiling.blit(halo, (x - panel, y - panel))
                pygame.draw.rect(ceiling, (252, 252, 244), cell.inflate(-2, -2))
                pygame.draw.rect(ceiling, (186, 184, 178), cell.inflate(-2, -2), 1)
            elif gx % 6 == 4 and gy % 4 == 3:                    # air vent
                v = cell.inflate(-panel // 4, -panel // 4)
                pygame.draw.rect(ceiling, (180, 180, 184), v)
                for i in range(v.y + 2, v.bottom - 1, 3):
                    pygame.draw.line(ceiling, (140, 140, 146), (v.x + 2, i), (v.right - 3, i), 1)
            elif rng.random() < 0.015:                           # sprinkler head
                pygame.draw.circle(ceiling, (170, 60, 50), cell.center, max(2, panel // 10))
    for part in (pygame.Rect(0, 0, w, room.y), pygame.Rect(0, room.bottom, w, h - room.bottom),
                 pygame.Rect(0, room.y, room.x, room.h), pygame.Rect(room.right, room.y, w - room.right, room.h)):
        surf.blit(ceiling, part.topleft, part)                   # ceiling everywhere except over the room
    lip = max(5, int(sq * 0.28))                                 # cut edge of the ceiling slab
    pygame.draw.rect(surf, (168, 164, 158), room.inflate(2 * lip, 2 * lip), lip)
    pygame.draw.rect(surf, (120, 116, 112), room.inflate(2, 2), 2)
    depth = max(6, int(sq * 0.45))                               # the overhang darkens the room's edges
    for i in range(depth):
        a = int(90 * (1 - i / depth) ** 2)
        shade = pygame.Surface((room.w - 2 * i, room.h - 2 * i), pygame.SRCALPHA)
        pygame.draw.rect(shade, (0, 0, 0, a), shade.get_rect(), 1)
        surf.blit(shade, (room.x + i, room.y + i))
    glass = room.inflate(-4, -4)                                 # window line along the outer walls
    pygame.draw.rect(surf, (170, 210, 235), glass, 2)
    for x in range(room.x, room.right, sq):
        pygame.draw.line(surf, (140, 180, 205), (x, room.y), (x, room.y + 5), 2)


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
        pass                                                      # indoors: the ceiling is drawn after the room
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
        _ceiling(background, game, (fx0, fy0, fx1, fy1), rng)

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
