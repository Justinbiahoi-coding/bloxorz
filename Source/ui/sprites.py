"""Generated art (assets/props, assets/textures). Every lookup returns None when a file is missing,
so the code-drawn fallback is used instead."""
from functools import lru_cache
from pathlib import Path

import pygame

ASSETS = Path(__file__).resolve().parent.parent / 'assets'


@lru_cache(maxsize=None)
def _load(path):
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return None


@lru_cache(maxsize=None)
def prop(name, w, h):
    """Prop sprite scaled to fit inside w x h (aspect kept), or None."""
    img = _load(ASSETS / 'props' / '{}.png'.format(name))
    if img is None or w < 2 or h < 2:
        return None
    k = min(w / img.get_width(), h / img.get_height())
    return pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))


@lru_cache(maxsize=None)
def texture(name, cell, span=4):
    """Seamless texture scaled so one copy covers span x span cells of ``cell`` px, or None."""
    img = _load(ASSETS / 'textures' / '{}.png'.format(name))
    if img is None:
        return None
    return pygame.transform.smoothscale(img.convert(), (cell * span, cell * span))


def fill(surf, rect, name, cell):
    """Tile a texture over ``rect``. Returns False when the texture is missing."""
    tex = texture(name, cell)
    if tex is None:
        return False
    clip = surf.get_clip()
    surf.set_clip(rect.clip(clip) if clip else rect)
    tw, th = tex.get_size()
    for y in range(rect.y, rect.bottom, th):
        for x in range(rect.x, rect.right, tw):
            surf.blit(tex, (x, y))
    surf.set_clip(clip)
    return True


def cell_piece(name, cell, x, y, span=4):
    """The part of a texture for grid cell (x, y), so neighbouring tiles continue the pattern."""
    tex = texture(name, cell, span)
    if tex is None:
        return None
    return tex.subsurface(((x % span) * cell, (y % span) * cell, cell, cell))
