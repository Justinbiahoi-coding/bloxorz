"""3D front-end (Ursina on Panda3D). Run with ``python main3d.py``."""


def run(fullscreen=True):
    from .world import ASSETS, configure, lights
    configure()
    from ursina import Entity, Text, Ursina, application
    app = Ursina(title='Bloxorz Tower', fullscreen=fullscreen, development_mode=False)
    application.asset_folder = ASSETS
    Entity.default_shader = None                 # use Panda3D's own lighting (see world.lights)
    Text.default_font = str(ASSETS / 'fonts' / 'Fredoka.ttf')
    from panda3d.core import NodePath  # noqa: F401  (render is a builtin set up by Ursina)
    import builtins
    sun = lights(builtins.render)
    from .game import TowerGame
    TowerGame(sun)
    app.run()
