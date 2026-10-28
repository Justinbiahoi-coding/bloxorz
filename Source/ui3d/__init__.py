"""3D front-end (Ursina on Panda3D). Run with ``python main3d.py``."""


def run(fullscreen=False, size=None):
    """size: window (width, height); by default most of the main monitor."""
    from .world import ASSETS, configure, lights
    configure()
    from ursina import Entity, Text, Ursina, application
    # a normal, large window by default: true fullscreen on macOS locks out Cmd+Tab and the Dock.
    # F toggles fullscreen when wanted.
    from screeninfo import get_monitors
    if size is None and not fullscreen:
        m = get_monitors()[0]
        size = (int(m.width * 0.9), int(m.height * 0.82))
    app = Ursina(title='Bloxorz Tower', fullscreen=fullscreen, borderless=False, size=size,
                 development_mode=False)
    application.asset_folder = ASSETS
    Entity.default_shader = None                 # use Panda3D's own lighting (see world.lights)
    from .theme import FONT_BODY
    Text.default_font = FONT_BODY                # Medium: the variable Fredoka loads as Light
    from panda3d.core import NodePath  # noqa: F401  (render is a builtin set up by Ursina)
    import builtins
    sun = lights(builtins.render)
    from .app import App3D
    App3D(sun)
    app.run()
