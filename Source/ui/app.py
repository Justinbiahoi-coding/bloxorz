import json
import os
import sys
from pathlib import Path

import pygame
import pygame_menu
from pygame.locals import QUIT

from engine import ALGORITHM_NAMES, GameSession

from .algorithm_views import AlgorithmMenu, AlgorithmShow
from .game import Game
from .tower_view import TowerGame

BASE_DIR = Path(__file__).resolve().parent.parent

# Graphics related
COLOR_BACKGROUND = [15, 125, 117]
FPS = 60

STATE_MENU = 'MENU'
STATE_INGAME = 'INGAME'
STATE_TOWER = 'TOWER'
STATE_VIEWING_STATS = 'VIEWING_STATS_ALGORITHM'
STATE_VIEWING_ALGORITHM = 'VIEWING_ALGORITHM'

ADVANCED_TILES = set('fshvlrkq')
TUTORIAL_LEVELS = (54, 55, 56, 57)
TUTORIAL_NAMES = {
    54: 'Tutorial 1 - Fragile',
    55: 'Tutorial 2 - Bridges',
    56: 'Tutorial 3 - Heavy Switch',
    57: 'Tutorial 4 - Split',
}
TUTORIAL_TIPS = {
    54: 'Fragile tiles break under a standing block. Roll across them lying down.',
    55: 'Soft switches open bridges. Closed bridges behave like void cells.',
    56: 'Heavy switches activate only when the full block stands upright on them.',
    57: 'Split switches divide the block into two cubes. Press SPACE to switch cubes, then bring them together to merge.',
}


def has_advanced_tiles(level_number):
    data = json.loads(
        (BASE_DIR / 'levels' / '{}.json'.format(level_number)).read_text(encoding='utf-8'))
    return bool(set(''.join(data.get('tiles', []))) & ADVANCED_TILES)


class App:
    """Pygame UI layer. Owns the window, menus and screen state machine."""

    def __init__(self):
        os.environ.setdefault('SDL_VIDEO_CENTERED', '1')
        # use the real X11 mode instead of the scaled logical desktop, so fullscreen opens once at its final size
        os.environ.setdefault('SDL_VIDEO_X11_XRANDR', '0')
        os.environ.setdefault('SDL_VIDEO_MAC_FULLSCREEN_SPACES', '1')   # macOS: fullscreen as its own Space, so Cmd+Tab and swipes still work
        pygame.init()

        self.clock = pygame.time.Clock()
        try:
            self.surface = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error:
            width, height = pygame.display.get_desktop_sizes()[0]
            self.surface = pygame.display.set_mode(
                (int(width * 0.9), int(height * 0.82)), pygame.RESIZABLE)
        pygame.event.pump()
        self.surface = pygame.display.get_surface()
        self.w, self.h = self.surface.get_size()
        pygame.display.set_caption('Bloxorz Tower')

        self.level_numbers = sorted(
            int(path.stem) for path in (BASE_DIR / 'levels').glob('*.json'))
        advanced_flags = {number: has_advanced_tiles(number)
                          for number in self.level_numbers}
        tutorials = [number for number in TUTORIAL_LEVELS
                     if number in self.level_numbers]
        self.normal_levels = [number for number in self.level_numbers
                              if not advanced_flags[number]]
        self.advanced_levels = tutorials + [
            number for number in self.level_numbers
            if advanced_flags[number] and number not in tutorials]
        if not self.normal_levels:
            self.normal_levels = list(self.level_numbers)

        self.play_mode = 'normal'
        self.play_levels = self.normal_levels
        self.free_play_level = self.play_levels[0] if self.play_levels else 1
        self.algorithm_mode = 'normal'
        self.algorithm_levels = self.normal_levels
        self.algorithm_level = self.algorithm_levels[0] if self.algorithm_levels else 1
        self.mode_selector = None
        self.free_map_selector = None
        self.algorithm_mode_selector = None
        self.algorithm_map_selector = None
        self.map_hint_label = None
        self.algorithm = 'DFS'

        self.state = STATE_MENU
        self.game = None
        self.algorithm_menu = None
        self.algorithm_show = None

        self.menu = None
        self.free_play_menu = None
        self.algorithms_select_menu = None
        self._build_menus()

    def _make_theme(self, background_color):
        k = max(1.0, min(3.0, self.h / 720))
        theme = pygame_menu.themes.THEME_DEFAULT.copy()
        theme.background_color = background_color
        theme.surface_clear_color = COLOR_BACKGROUND
        theme.title_background_color = (120, 45, 30)
        theme.title_font = pygame_menu.font.FONT_NEVIS
        theme.title_font_color = (255, 255, 255)
        theme.title_font_size = int(50 * k)
        theme.widget_font = pygame_menu.font.FONT_FRANCHISE
        theme.widget_font_color = (255, 255, 255)
        theme.widget_font_size = int(36 * k)
        theme.widget_margin = (0, int(8 * k))
        theme.widget_padding = (int(4 * k), int(8 * k))
        return theme

    def _build_menus(self):
        self.menu = pygame_menu.Menu(
            title='Bloxorz Menu',
            width=self.w,
            height=self.h,
            surface=self.surface,
            theme=self._make_theme(COLOR_BACKGROUND),
            onclose=pygame_menu.events.NONE,
        )

        self.free_play_menu = pygame_menu.Menu(
            title='Free Play',
            width=self.w,
            height=self.h,
            surface=self.surface,
            theme=self._make_theme((30, 50, 107)),
            onclose=pygame_menu.events.NONE,
        )
        self.mode_selector = self.free_play_menu.add.selector(
            'Mode',
            [('Normal', 'normal'), ('Advanced', 'advanced')],
            onreturn=None, onchange=self._on_mode_change)
        self.free_map_selector = self.free_play_menu.add.selector(
            'Map', self._map_items(self.play_levels),
            onreturn=None, onchange=self._on_free_map_change)
        self.map_hint_label = self.free_play_menu.add.label(
            '', max_char=70, wordwrap=True,
            font_size=int(22 * max(1.0, min(3.0, self.h / 720))))
        self._refresh_map_hint()
        self.free_play_menu.add.button('Start', self._start_free_play)
        self.free_play_menu.add.button(
            'Return to Menu', pygame_menu.events.BACK)

        self.algorithms_select_menu = pygame_menu.Menu(
            title='Algorithms',
            width=self.w,
            height=self.h,
            surface=self.surface,
            theme=self._make_theme((27, 90, 26)),
            onclose=pygame_menu.events.NONE,
        )
        self.algorithm_mode_selector = self.algorithms_select_menu.add.selector(
            'Mode',
            [('Normal', 'normal'), ('Advanced', 'advanced')],
            onreturn=None, onchange=self._on_algorithm_mode_change)
        self.algorithm_map_selector = self.algorithms_select_menu.add.selector(
            'Map', self._map_items(self.algorithm_levels),
            onreturn=None, onchange=self._on_algorithm_map_change)
        self.algorithms_select_menu.add.selector(
            'Algorithm',
            [(name, name) for name in ALGORITHM_NAMES],
            onreturn=None, onchange=self._on_algorithm_change)
        self.algorithms_select_menu.add.button(
            'Start', self._start_algorithms)
        self.algorithms_select_menu.add.button(
            'Return to Menu', pygame_menu.events.BACK)

        self.menu.add.button('Tower', self._start_tower)
        self.menu.add.button('Free Play', self.free_play_menu)
        self.menu.add.button('Algorithms', self.algorithms_select_menu)
        self.menu.add.button('Exit', pygame_menu.events.EXIT)

    def _selected_option_value(self, value):
        # pygame-menu passes (selected_item, selected_index) as the first
        # argument, but older/newer versions may pass the item directly.
        if (isinstance(value, tuple) and value
                and isinstance(value[0], tuple)):
            value = value[0]
        return value[1]

    def _map_label(self, level_number):
        return TUTORIAL_NAMES.get(level_number, 'Level {}'.format(level_number))

    def _map_items(self, levels):
        return [(self._map_label(number), number) for number in levels]

    def _refresh_map_hint(self):
        if self.map_hint_label is None:
            return
        tip = TUTORIAL_TIPS.get(self.free_play_level)
        if tip:
            self.map_hint_label.set_title(tip)
            self.map_hint_label.show()
        else:
            self.map_hint_label.set_title('')
            self.map_hint_label.hide()

    def _set_play_mode(self, mode, level_number=None):
        if mode not in ('normal', 'advanced'):
            mode = 'normal'
        levels = self.advanced_levels if mode == 'advanced' else self.normal_levels
        if not levels:
            levels = list(self.level_numbers)
        if level_number not in levels:
            level_number = levels[0] if levels else 1
        self.play_mode = mode
        self.play_levels = levels
        self.free_play_level = level_number
        if self.mode_selector is not None:
            self.mode_selector.set_value(0 if mode == 'normal' else 1)
        if self.free_map_selector is not None:
            self.free_map_selector.update_items(self._map_items(levels))
            self.free_map_selector.set_value(levels.index(level_number))
        self._refresh_map_hint()

    def _on_mode_change(self, value, *args, **kwargs):
        self._set_play_mode(self._selected_option_value(value))

    def _on_free_map_change(self, value, *args, **kwargs):
        self.free_play_level = self._selected_option_value(value)
        self._refresh_map_hint()

    def _set_algorithm_mode(self, mode, level_number=None):
        if mode not in ('normal', 'advanced'):
            mode = 'normal'
        levels = self.advanced_levels if mode == 'advanced' else self.normal_levels
        if not levels:
            levels = list(self.level_numbers)
        if level_number not in levels:
            level_number = levels[0] if levels else 1
        self.algorithm_mode = mode
        self.algorithm_levels = levels
        self.algorithm_level = level_number
        if self.algorithm_mode_selector is not None:
            self.algorithm_mode_selector.set_value(0 if mode == 'normal' else 1)
        if self.algorithm_map_selector is not None:
            self.algorithm_map_selector.update_items(self._map_items(levels))
            self.algorithm_map_selector.set_value(levels.index(level_number))

    def _on_algorithm_mode_change(self, value, *args, **kwargs):
        self._set_algorithm_mode(self._selected_option_value(value))

    def _on_algorithm_map_change(self, value, *args, **kwargs):
        self.algorithm_level = self._selected_option_value(value)

    def _on_algorithm_change(self, value, *args, **kwargs):
        self.algorithm = self._selected_option_value(value)

    def _start_free_play(self, level_number=None):
        if level_number is not None:
            self.free_play_level = level_number
        self.menu.disable()
        self.surface.fill(COLOR_BACKGROUND)
        session = GameSession(self.free_play_level)
        self.game = Game(self.surface, self.h, self.w, session,
                         show_hint=False, free_play=True,
                         has_next=self._next_level_number(self.free_play_level) is not None,
                         tip=TUTORIAL_TIPS.get(self.free_play_level))
        self.state = STATE_INGAME
        self._play_music()

    def _next_level_number(self, level_number):
        try:
            index = self.play_levels.index(level_number)
        except ValueError:
            return None
        if index + 1 < len(self.play_levels):
            return self.play_levels[index + 1]
        return None

    def _start_tower(self):
        self.menu.disable()
        self.tower = TowerGame(self.surface, self.h, self.w)
        self.state = STATE_TOWER

    def _start_algorithms(self):
        self.menu.disable()
        self.algorithm_menu = AlgorithmMenu(
            self.surface, self.h, self.w, self.algorithm_level, self.algorithm)
        self.state = STATE_VIEWING_STATS

    def _play_music(self):
        try:
            pygame.mixer.music.load(str(BASE_DIR / 'assets' / 'tetris.mp3'))
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.05)
        except pygame.error:
            pass

    def _return_to_menu(self):
        self.state = STATE_MENU
        pygame.mixer.music.stop()
        self.menu.full_reset()
        self._set_play_mode(self.play_mode, self.free_play_level)
        self._set_algorithm_mode(self.algorithm_mode, self.algorithm_level)
        self.menu.enable()

    def _update(self, events, deltatime):
        if self.state == STATE_INGAME:
            self.game.process(events)
            if self.game.command == 'menu':
                self._return_to_menu()
            elif self.game.command == 'retry':
                self._start_free_play(self.game.session.level_number)
            elif self.game.command == 'next':
                next_level = self._next_level_number(self.game.session.level_number)
                if next_level is not None:
                    self._start_free_play(next_level)
            elif self.game.should_quit():
                self._return_to_menu()
        elif self.state == STATE_TOWER:
            self.tower.process(events)
            if self.tower.should_quit():
                self._return_to_menu()
        elif self.state == STATE_VIEWING_STATS:
            self.algorithm_menu.process(events)
            if self.algorithm_menu.should_quit():
                self._return_to_menu()
            else:
                solution = self.algorithm_menu.show_solution()
                if solution is not None:
                    self.state = STATE_VIEWING_ALGORITHM
                    self.algorithm_show = AlgorithmShow(
                        self.surface, self.h, self.w, self.algorithm_level, solution,
                        "Level {}, Algorithm {}, Showing Solution".format(
                            self.algorithm_level, self.algorithm), 500)
                explored_nodes = self.algorithm_menu.show_explored_nodes()
                if explored_nodes is not None:
                    self.state = STATE_VIEWING_ALGORITHM
                    self.algorithm_show = AlgorithmShow(
                        self.surface, self.h, self.w, self.algorithm_level,
                        explored_nodes,
                        "Level {}, Algorithm {}, Showing Explored Nodes".format(
                            self.algorithm_level, self.algorithm), 150, False)
        elif self.state == STATE_VIEWING_ALGORITHM:
            self.algorithm_show.process(events, deltatime)
            if self.algorithm_show.should_quit():
                self._return_to_menu()
        elif self.state == STATE_MENU:
            self.menu.update(events)
            if self.menu.is_enabled():
                self.menu.draw(self.surface, clear_surface=False)

    def run(self):
        while True:
            deltatime = self.clock.tick(FPS)
            self.surface.fill(COLOR_BACKGROUND)
            events = pygame.event.get()

            for event in events:
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()

            self._update(events, deltatime)
            pygame.display.flip()


def run():
    App().run()
