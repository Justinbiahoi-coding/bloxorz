"""Screens of the 3D front-end and how they lead into each other.

  Loading -> opening film (any key skips) -> title shot with the main menu
      Tower        the climb, walking in through the doors (Justin's TowerGame)
      Free Play    level select over the title shot -> FreePlayGame -> result -> next / retry / levels
      Algorithms   the solver lab (screens/algorithms.py)
      Settings     a dialog over whatever is on screen
  Every game has a HUD with New Game, Restart, Hint, Solve and Pause; Esc pauses.
"""
from ursina import Entity, invoke, window

from engine.catalog import level_label
from . import audio, settings
from . import widgets as w
from .free_play import FreePlayGame
from .game import TowerGame
from .screens.algorithms import AlgorithmsLab
from .screens.dialogs import ResultDialog
from .screens.level_select import LevelSelect
from .screens.loading import LoadingScreen
from .screens.main_menu import MainMenu
from .screens.settings_screen import SettingsScreen, apply_all


class App3D(Entity):
    def __init__(self, sun):
        super().__init__()
        window.title = 'Bloxorz Tower'
        self.sun = sun
        self.scene = None             # TowerGame, FreePlayGame or AlgorithmsLab
        self.menu_root = None         # MainMenu or LevelSelect
        self.loading_root = None
        self.state = 'loading'
        self.first_title = True       # the opening film plays in full only the first time
        self.free_mode, self.free_level = 'normal', None
        settings.load()
        apply_all()
        audio.start()
        self.main_menu()

    # ---- plumbing ----
    def _clear_menu(self):
        if self.menu_root is not None:
            self.menu_root.close()
            self.menu_root = None

    def _clear_scene(self):
        for m in list(w.Modal.stack):
            m.close()
        if self.scene is not None:
            self.scene.close()
            self.scene = None

    def _clear_loading(self):
        if self.loading_root is not None:
            self.loading_root.close()
            self.loading_root = None

    def _load(self, caption, build, then=None):
        """Show the loading screen, run build() (which returns the new scene), then call then()."""
        self._clear_menu()
        self._clear_scene()
        self._clear_loading()
        self.state = 'loading'
        self.loading_root = LoadingScreen(caption)

        def steps():
            yield .2, caption
            self.scene = build()
            yield 1.0, 'Ready'

        def done():
            self._clear_loading()
            if then:
                then()
        self.loading_root.run(steps(), done)

    def _later(self, fn, *args):
        invoke(fn, *args, delay=.01)          # leave the current input/update before tearing scenes down

    @property
    def _title_up(self):
        """The title shot is still standing behind the menus."""
        return isinstance(self.scene, TowerGame) and self.scene.menu_hold

    # ---- main menu: the opening's title shot ----
    def main_menu(self):
        if self._title_up:
            self._show_main_menu()
            return
        self._load('Loading', self._build_title, self._await_title)

    def _new_tower_game(self):
        return TowerGame(self.sun, on_menu=self._to_menu, on_new_game=self.new_tower,
                         on_settings=self.open_settings, on_finish=self._tower_done)

    def _build_title(self):
        scene = self._new_tower_game()
        scene.menu_hold = True
        scene.intro.show_button = False
        if not self.first_title:                 # back from a game: straight to the title shot
            scene.intro.skip_or_enter()
        self.first_title = False
        return scene

    def _await_title(self):
        self.state = 'intro'                     # update() opens the menu once the title is up

    def update(self):
        if self.state == 'intro' and self._title_up and self.scene.intro.at_title:
            self._show_main_menu()

    def _title_letters(self, on):
        if self._title_up:
            self.scene.intro.title.enabled = self.scene.intro.sub.enabled = on

    def _show_main_menu(self):
        self._clear_menu()
        self._title_letters(True)
        self.state = 'main'
        self.menu_root = MainMenu({
            'tower': self._enter_tower,
            'free_play': lambda: self.open_levels(),
            'algorithms': self.open_algorithms,
            'settings': lambda: self.open_settings(),
        })

    def _to_menu(self):
        self._later(self._go_menu)

    def _go_menu(self):
        self._clear_menu()
        if not self._title_up:
            self._clear_scene()
        self.main_menu()

    # ---- tower ----
    def _enter_tower(self):
        self._clear_menu()
        self.state = 'game'
        self.scene.menu_hold = False
        self.scene.intro.skip_or_enter()         # at the title this walks into the lobby

    def new_tower(self):
        self._later(self._load, 'Back to the lobby', self._build_tower_skip, self._playing)

    def _build_tower_skip(self):
        scene = self._new_tower_game()
        scene.intro.done = True                  # no film: straight into the lobby
        return scene

    def _tower_done(self, floors, moves):
        ResultDialog(True, moves, title='Tower cleared', on_retry=self.new_tower, on_menu=self._to_menu)

    def _playing(self):
        self.state = 'game'

    # ---- free play ----
    def open_levels(self, mode=None, level=None):
        if mode is not None:
            self.free_mode, self.free_level = mode, level
        self._clear_menu()
        if not self._title_up:
            self._clear_scene()
        self.state = 'levels'
        self._title_letters(False)
        self.menu_root = LevelSelect(self.start_free_play, self._levels_back, self.free_mode, self.free_level)

    def _levels_back(self):
        self._later(self._go_menu)

    def start_free_play(self, level, mode=None):
        self.free_level = level
        if mode is not None:
            self.free_mode = mode
        self._later(self._load, 'Loading {}'.format(level_label(level)), self._build_free_play, self._playing)

    def _build_free_play(self):
        level, mode = self.free_level, self.free_mode
        return FreePlayGame(self.sun, level, mode, on_menu=self._to_menu,
                            on_next=lambda n: self.start_free_play(n, mode),
                            on_levels=lambda: self._later(self.open_levels, mode, level),
                            on_settings=self.open_settings)

    # ---- algorithms ----
    def open_algorithms(self):
        self._later(self._load, 'Loading the solver lab', lambda: AlgorithmsLab(self.sun, self._to_menu),
                    lambda: setattr(self, 'state', 'algorithms'))

    # ---- settings ----
    def open_settings(self, on_close=None):
        SettingsScreen(on_close)

    # ---- keys for the menus ----
    def input(self, key):
        if key == 'f' and self.state in ('main', 'levels', 'loading', 'intro') and not w.Modal.any_open():
            settings.set('fullscreen', not window.fullscreen)
            apply_all()
