"""3D front-end (Ursina on Panda3D). Run with ``python main3d.py``."""


def run(fullscreen=False):
    from .world import ASSETS, FONT, configure, lights
    configure()
    from ursina import Entity, Text, Ursina, application
    # a normal, large window by default: true fullscreen on macOS locks out Cmd+Tab and the Dock.
    # F toggles fullscreen when wanted.
    from screeninfo import get_monitors
    m = get_monitors()[0]
    size = (int(m.width * 0.9), int(m.height * 0.82)) if not fullscreen else None
    app = Ursina(title='Bloxorz Tower', fullscreen=fullscreen, borderless=False, size=size,
                 development_mode=False)
    application.asset_folder = ASSETS
    Entity.default_shader = None                 # use Panda3D's own lighting (see world.lights)
    Text.default_font = FONT
    from panda3d.core import NodePath  # noqa: F401  (render is a builtin set up by Ursina)
    import builtins
    sun = lights(builtins.render)
    from .game import TowerGame
    TowerGame(sun)
    app.run()
