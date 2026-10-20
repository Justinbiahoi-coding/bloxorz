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
H_SIZE = 650  # Height of window size
W_SIZE = 880  # Width of window size

STATE_MENU = 'MENU'
STATE_INGAME = 'INGAME'
STATE_TOWER = 'TOWER'
STATE_VIEWING_STATS = 'VIEWING_STATS_ALGORITHM'
STATE_VIEWING_ALGORITHM = 'VIEWING_ALGORITHM'


class App:
    """Pygame UI layer. Owns the window, menus and screen state machine."""

    def __init__(self):
        os.environ.setdefault('SDL_VIDEO_CENTERED', '1')
        pygame.init()

        self.clock = pygame.time.Clock()
        self.surface = pygame.display.set_mode((W_SIZE, H_SIZE))
        pygame.display.set_caption('Bloxorz Menu')

        self.level_numbers = sorted(
            int(path.stem) for path in (BASE_DIR / 'levels').glob('*.json'))
        self.map_menu_array = [(str(number), number)
                               for number in self.level_numbers]
        self.map_number = self.level_numbers[0] if self.level_numbers else 1
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
        theme = pygame_menu.themes.THEME_DEFAULT.copy()
        theme.background_color = background_color
        theme.surface_clear_color = COLOR_BACKGROUND
        theme.title_background_color = (120, 45, 30)
        theme.title_font = pygame_menu.font.FONT_NEVIS
        theme.title_font_color = (255, 255, 255)
        theme.title_font_size = 50
        theme.widget_font = pygame_menu.font.FONT_FRANCHISE
        theme.widget_font_color = (255, 255, 255)
        theme.widget_font_size = 36
        theme.widget_margin = (0, 8)
        return theme

    def _build_menus(self):
        self.menu = pygame_menu.Menu(
            title='Bloxorz Menu',
            width=W_SIZE,
            height=H_SIZE,
            surface=self.surface,
            theme=self._make_theme(COLOR_BACKGROUND),
            onclose=pygame_menu.events.NONE,
        )

        self.free_play_menu = pygame_menu.Menu(
            title='Free Play',
            width=W_SIZE,
            height=H_SIZE,
            surface=self.surface,
            theme=self._make_theme((30, 50, 107)),
            onclose=pygame_menu.events.NONE,
        )
        self.free_play_menu.add.selector(
            'Map', self.map_menu_array,
            onreturn=None, onchange=self._on_map_change)
        self.free_play_menu.add.button('Start', self._start_free_play)
        self.free_play_menu.add.button(
            'Return to Menu', pygame_menu.events.BACK)

        self.algorithms_select_menu = pygame_menu.Menu(
            title='Algorithms',
            width=W_SIZE,
            height=H_SIZE,
            surface=self.surface,
            theme=self._make_theme((27, 90, 26)),
            onclose=pygame_menu.events.NONE,
        )
        self.algorithms_select_menu.add.selector(
            'Map', self.map_menu_array,
            onreturn=None, onchange=self._on_map_change)
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

    def _on_map_change(self, value, *args, **kwargs):
        self.map_number = self._selected_option_value(value)

    def _on_algorithm_change(self, value, *args, **kwargs):
        self.algorithm = self._selected_option_value(value)

    def _start_free_play(self):
        self.menu.disable()
        self.surface.fill(COLOR_BACKGROUND)
        session = GameSession(self.map_number)
        self.game = Game(self.surface, H_SIZE, W_SIZE, session, True)
        self.state = STATE_INGAME
        self._play_music()

    def _start_tower(self):
        self.menu.disable()
        self.tower = TowerGame(self.surface, H_SIZE, W_SIZE)
        self.state = STATE_TOWER

    def _start_algorithms(self):
        self.menu.disable()
        self.algorithm_menu = AlgorithmMenu(
            self.surface, H_SIZE, W_SIZE, self.map_number, self.algorithm)
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
        self.menu.enable()

    def _update(self, events, deltatime):
        if self.state == STATE_INGAME:
            self.game.process(events)
            if self.game.should_quit():
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
                        self.surface, H_SIZE, W_SIZE, self.map_number, solution,
                        "Level {}, Algorithm {}, Showing Solution".format(
                            self.map_number, self.algorithm), 500)
                explored_nodes = self.algorithm_menu.show_explored_nodes()
                if explored_nodes is not None:
                    self.state = STATE_VIEWING_ALGORITHM
                    self.algorithm_show = AlgorithmShow(
                        self.surface, H_SIZE, W_SIZE, self.map_number,
                        explored_nodes,
                        "Level {}, Algorithm {}, Showing Explored Nodes".format(
                            self.map_number, self.algorithm), 150, False)
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
