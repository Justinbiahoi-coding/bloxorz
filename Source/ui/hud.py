"""Shared look for the tower mode: palette, Fredoka font, HUD panels and the building progress meter."""
from pathlib import Path

import pygame

FONT_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'fonts' / 'Fredoka.ttf'
INK, PAPER, GOLD, CORAL = (27, 37, 64), (250, 244, 232), (255, 200, 87), (255, 138, 91)
_fonts = {}


def font(size):
    if size not in _fonts:
        try:
            _fonts[size] = pygame.font.Font(str(FONT_PATH), size)
            _fonts[size].set_bold(True)   # the variable font loads at its lightest weight
        except (FileNotFoundError, pygame.error):
            _fonts[size] = pygame.font.Font(None, int(size * 1.2))
    return _fonts[size]


def scale(surf):
    """UI scale: 1 up to a 720px-high screen, growing to 1.8 on big displays."""
    return max(1.0, min(1.8, surf.get_height() / 720))


def text(surf, string, size, color, **anchor):
    img = font(int(size * scale(surf))).render(string, True, color)
    surf.blit(img, img.get_rect(**anchor))
    return img.get_rect(**anchor)


def panel(surf, rect, alpha=185):
    layer = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(layer, (*INK, alpha), layer.get_rect(), border_radius=16)
    pygame.draw.rect(layer, (*PAPER, 40), layer.get_rect(), 1, border_radius=16)
    surf.blit(layer, rect.topleft)


def floor_name(floor, count):
    """Building names, top floor first: ROOFTOP, FLOOR n ... FLOOR 1, LOBBY."""
    if floor == 0:
        return 'ROOFTOP'
    if floor == count - 1:
        return 'LOBBY'
    return 'FLOOR {}'.format(count - 1 - floor)


def draw_hud(surf, floor, count, moves):
    """Top-left card: where you are in the building and the moves taken on this floor."""
    k = scale(surf)
    box = pygame.Rect(int(20 * k), int(20 * k), int(270 * k), int(82 * k))
    panel(surf, box)
    pad = int(18 * k)
    text(surf, 'LEVEL {} / {}'.format(floor + 1, count), 15, GOLD, topleft=(box.x + pad, box.y + int(10 * k)))
    text(surf, floor_name(floor, count), 34, PAPER, topleft=(box.x + pad, box.y + int(28 * k)))
    text(surf, str(moves), 34, PAPER, topright=(box.right - pad, box.y + int(28 * k)))
    text(surf, 'MOVES', 15, GOLD, topright=(box.right - pad, box.y + int(10 * k)))


def draw_tower(surf, floor, count):
    """Right edge: the building as a stack of floors; the one you are on glows."""
    k = scale(surf)
    w, h = surf.get_size()
    bar = int(24 * k)
    top, bottom, x = int(110 * k), h - int(70 * k), w - int(44 * k)
    slot = (bottom - top) / count
    for i in range(count):
        rect = pygame.Rect(x, int(top + i * slot) + 2, bar, max(4, int(slot) - 5))
        if i == floor:
            glow = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*CORAL, 90), glow.get_rect(), border_radius=10)
            surf.blit(glow, (rect.x - 8, rect.y - 8))
            color = CORAL
        else:
            color = GOLD if i < floor else (*PAPER, 110)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, color, layer.get_rect(), border_radius=5)
        surf.blit(layer, rect.topleft)
    text(surf, 'ROOF', 13, PAPER, midbottom=(x + bar // 2, top - 4))
    text(surf, 'LOBBY', 13, PAPER, midtop=(x + bar // 2, bottom + 4))


def draw_finish(surf, total_moves, count):
    k = scale(surf)
    w, h = surf.get_size()
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    shade.fill((*INK, 150))
    surf.blit(shade, (0, 0))
    box = pygame.Rect(0, 0, int(440 * k), int(230 * k))
    box.center = (w // 2, h // 2)
    panel(surf, box, 235)
    text(surf, 'GROUND FLOOR', 16, GOLD, midtop=(box.centerx, box.y + int(26 * k)))
    text(surf, 'You made it down', 40, PAPER, midtop=(box.centerx, box.y + int(52 * k)))
    text(surf, '{} floors  -  {} moves'.format(count, total_moves), 26, PAPER, midtop=(box.centerx, box.y + int(112 * k)))
    text(surf, 'Press ESC for the menu', 20, CORAL, midtop=(box.centerx, box.y + int(168 * k)))
