"""Main menu, Free Play selection, and scene switching for the 3D front-end."""
from ursina import Button, Entity, Text, application, camera, color, destroy, invoke, window

from engine.catalog import TUTORIAL_TIPS, level_label, levels_for_mode

from .free_play import FreePlayGame
from .game import TowerGame


class App3D(Entity):
    def __init__(self, sun):
        super().__init__()
        window.title = 'Bloxorz Tower'
        self.sun = sun
        self.scene = None
        self.menu_root = None
        self.loading_root = None
        self.state = 'main'
        self.free_mode = 'normal'
        levels = levels_for_mode(self.free_mode)
        self.free_level = levels[0] if levels else 1
        self.main_menu()

    # ---- cleanup ----
    def _clear_menu(self):
        if self.menu_root is not None:
            destroy(self.menu_root)
            self.menu_root = None

    def _clear_scene(self):
        if self.scene is not None:
            if hasattr(self.scene, 'close'):
                self.scene.close()
            else:
                destroy(self.scene)
            self.scene = None

    def _new_menu(self):
        self._clear_menu()
        self.menu_root = Entity(parent=camera.ui)

    def _clear_loading(self):
        if self.loading_root is not None:
            destroy(self.loading_root)
            self.loading_root = None

    def _show_loading(self, message):
        self._clear_menu()
        self._clear_scene()
        self._clear_loading()
        self.state = 'loading'
        window.color = color.rgb(8, 12, 26)
        self.loading_root = Entity(parent=camera.ui)
        Text(message, parent=self.loading_root, origin=(0, 0), scale=2.2,
             color=color.rgb(255, 200, 87))

    def _button(self, text, y, on_click, **kwargs):
        return Button(text, parent=self.menu_root, scale=(.5, .075), y=y,
                      color=color.rgb(44, 58, 94), on_click=on_click, **kwargs)

    def _game_menu(self):
        invoke(self.main_menu, delay=.01)

    def _game_next(self, level_number):
        invoke(lambda: self.start_free_play(level_number), delay=.01)

    # ---- main menu ----
    def main_menu(self):
        self._clear_scene()
        self._clear_menu()
        self.state = 'main'
        window.color = color.rgb(8, 12, 26)
        self._new_menu()
        Text('BLOXORZ', parent=self.menu_root, origin=(0, 0), y=.34, scale=8,
             color=color.rgb(255, 200, 87))
        Text('T O W E R', parent=self.menu_root, origin=(0, 0), y=.26, scale=2.6,
             color=color.rgb(255, 138, 91))
        self._button('Tower', .11, self.start_tower)
        self._button('Free Play', .01, self.free_play_menu)
        self._button('Algorithms', -.09, self._algorithms_notice)
        self._button('Exit', -.19, application.quit)
        self.notice = Text('', parent=self.menu_root, origin=(0, 0), y=-.31, scale=1.1,
                           color=color.rgb(200, 206, 224))

    def _algorithms_notice(self):
        if getattr(self, 'notice', None) is not None:
            self.notice.text = 'Algorithms mode is not available in the 3D front-end yet.'

    # ---- free play menu ----
    def free_play_menu(self):
        self._clear_scene()
        self._clear_menu()
        self.state = 'free'
        window.color = color.rgb(8, 12, 26)
        self._new_menu()
        Text('FREE PLAY', parent=self.menu_root, origin=(0, 0), y=.34, scale=5,
             color=color.rgb(255, 200, 87))
        self.mode_button = self._button('', .17, self.toggle_mode)
        self.mode_prev = Button('<', parent=self.menu_root, x=-.32, y=.17,
                                scale=(.07, .075), color=color.rgb(44, 58, 94),
                                on_click=self.toggle_mode)
        self.mode_prev.text_entity.use_tags = False
        self.mode_prev.text = '<'
        self.mode_next = Button('>', parent=self.menu_root, x=.32, y=.17,
                                scale=(.07, .075), color=color.rgb(44, 58, 94),
                                on_click=self.toggle_mode)
        self.mode_next.text_entity.use_tags = False
        self.mode_next.text = '>'
        self.prev_button = Button('Prev', parent=self.menu_root, x=-.38, y=.05,
                                  scale=(.16, .075), color=color.rgb(44, 58, 94),
                                  on_click=lambda: self.move_level(-1))
        self.level_label = Text('', parent=self.menu_root, origin=(0, 0), y=.05, scale=2.2,
                                color=color.white)
        self.next_button = Button('Next', parent=self.menu_root, x=.38, y=.05,
                                  scale=(.16, .075), color=color.rgb(44, 58, 94),
                                  on_click=lambda: self.move_level(1))
        self.tip = Text('', parent=self.menu_root, origin=(0, 0), y=-.07, scale=1.1,
                        wordwrap=70, background=True, color=color.rgb(250, 244, 232))
        self._button('Start', -.20, self.start_free_play)
        self._button('Back', -.30, self.main_menu)
        self.refresh_free_menu()

    def toggle_mode(self):
        self.free_mode = 'advanced' if self.free_mode == 'normal' else 'normal'
        levels = levels_for_mode(self.free_mode)
        self.free_level = levels[0] if levels else 1
        self.refresh_free_menu()

    def move_level(self, step):
        levels = levels_for_mode(self.free_mode)
        if not levels:
            return
        try:
            index = levels.index(self.free_level)
        except ValueError:
            index = 0
        self.free_level = levels[(index + step) % len(levels)]
        self.refresh_free_menu()

    def refresh_free_menu(self):
        if getattr(self, 'mode_button', None) is None:
            return
        self.mode_button.text = 'Mode: {}'.format('Normal' if self.free_mode == 'normal' else 'Advanced')
        self.level_label.text = level_label(self.free_level)
        tip = TUTORIAL_TIPS.get(self.free_level)
        self.tip.text = tip or 'Choose a stage and press Start.'

    # ---- scene starts ----
    def start_tower(self):
        self._show_loading('Loading tower...')
        invoke(self._load_tower, delay=.05)

    def _load_tower(self):
        self.scene = TowerGame(self.sun, on_menu=self._game_menu)
        self._clear_loading()
        self.state = 'game'

    def start_free_play(self, level_number=None):
        if level_number is not None:
            self.free_level = level_number
        self._show_loading('Loading {}...'.format(level_label(self.free_level)))
        invoke(self._load_free_play, delay=.05)

    def _load_free_play(self):
        self.scene = FreePlayGame(self.sun, self.free_level, self.free_mode,
                                  on_menu=self._game_menu, on_next=self._game_next)
        self._clear_loading()
        self.state = 'game'

    # ---- input for menus ----
    def input(self, key):
        if self.state in ('main', 'free', 'loading'):
            if key == 'f':
                window.fullscreen = not window.fullscreen
                return
        if self.state == 'free':
            if key == 'escape':
                self.main_menu()
            elif key == 'left arrow':
                self.move_level(-1)
            elif key == 'right arrow':
                self.move_level(1)
            elif key in ('enter', 'space'):
                self.start_free_play()
        elif self.state == 'main' and key == 'escape':
            application.quit()
