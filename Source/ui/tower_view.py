"""Tower mode: play floor after floor; winning drops the block through the hole to the next floor."""
from pathlib import Path

import pygame

from engine import Tower

from . import hud
from .game import Game
from .intro import Intro

BACKGROUNDS = Path(__file__).resolve().parent.parent / 'assets' / 'backgrounds'
THEMES = 4            # sky_0 (golden hour) .. sky_3 (night): the sky darkens as you go down
FALL_MS, SLIDE_MS, ENTER_MS = 380, 620, 750


def _ease(t):
    return t * t * (3 - 2 * t)


class TowerGame:
    def __init__(self, surface, height, width):
        self.surface, self.h, self.w = surface, height, width
        self.tower = Tower()
        self.skies = {}
        self.game = self._make_game(surface)
        self.intro = Intro(surface, width, height)
        self.phase, self.t0 = 'intro', 0
        self.old = self.new = None
        self.quit = False

    def _sky(self):
        i = min(THEMES - 1, self.tower.index * THEMES // self.tower.count)
        if i not in self.skies:
            try:
                img = pygame.image.load(str(BACKGROUNDS / 'sky_{}.png'.format(i))).convert()
                k = max(self.w / img.get_width(), self.h / img.get_height())     # cover the screen, crop the rest
                big = pygame.transform.smoothscale(img, (int(img.get_width() * k) + 1, int(img.get_height() * k) + 1))
                self.skies[i] = big.subsurface(((big.get_width() - self.w) // 2, (big.get_height() - self.h) // 2, self.w, self.h)).copy()
            except (FileNotFoundError, pygame.error):
                self.skies[i] = None        # Game falls back to the procedural sky
        return self.skies[i]

    def _make_game(self, surface):
        return Game(surface, self.h, self.w, self.tower.session, False, self._sky(),
                    scene=(self.tower.index, self.tower.count))

    def should_quit(self):
        return self.quit or self.game.should_quit()

    def process(self, events):
        now = pygame.time.get_ticks()
        elapsed = now - self.t0
        if self.phase == 'intro':
            if any(e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE for e in events):
                self.quit = True
                return
            self.intro.process(events)
            if self.intro.finished:                       # dive into the roof
                self.old = self.surface.copy()
                self.new = pygame.Surface((self.w, self.h))
                self._make_game(self.new).draw()
                self.phase, self.t0 = 'enter', now
            return
        if self.phase == 'enter':
            e = _ease(min(1, elapsed / ENTER_MS))
            self.surface.blit(self.new, (0, 0))
            zoom = 1 + 1.2 * e                            # the intro frame grows towards the roof and fades
            big = pygame.transform.scale(self.old, (int(self.w * zoom), int(self.h * zoom)))
            cx, cy = self.w // 2, self.intro.roof_y
            big.set_alpha(int(255 * (1 - e)))
            self.surface.blit(big, (cx - cx * zoom, cy - cy * zoom))
            if elapsed >= ENTER_MS:
                self.phase = 'play'
            hud.draw_hud(self.surface, self.tower.index, self.tower.count, self.tower.session.moves)
            hud.draw_tower(self.surface, self.tower.index, self.tower.count)
            return
        if self.phase == 'play':
            self.game.process_input(events)
            self.game.draw()
            if self.tower.session.won:
                self.phase, self.t0 = 'fall', now
        elif self.phase == 'fall':
            self.game.block_scale = max(0.0, 1 - _ease(min(1, elapsed / FALL_MS)))
            self.game.draw()
            if elapsed >= FALL_MS:
                self.game.block_scale = 1.0
                if self.tower.is_last:
                    self.phase = 'finish'
                else:
                    self.old = self.surface.copy()
                    self.tower.descend()
                    self.new = pygame.Surface((self.w, self.h))
                    self._make_game(self.new).draw()
                    self.phase, self.t0 = 'slide', now
        elif self.phase == 'slide':
            e = _ease(min(1, elapsed / SLIDE_MS))
            self.surface.blit(self.old, (0, -int(self.h * e)))      # old floor leaves upward,
            self.surface.blit(self.new, (0, int(self.h * (1 - e))))  # the next one rises from below
            if elapsed >= SLIDE_MS:
                self.game = self._make_game(self.surface)
                self.phase = 'play'
        else:  # finish
            self.game.process_input(events)
            self.game.draw()
            hud.draw_finish(self.surface, self.tower.total_moves + self.tower.session.moves, self.tower.count)
            return
        hud.draw_hud(self.surface, self.tower.index, self.tower.count, self.tower.session.moves)
        hud.draw_tower(self.surface, self.tower.index, self.tower.count)
