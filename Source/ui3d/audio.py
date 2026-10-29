"""Background music: assets/tetris.mp3 on a loop, at the volume from settings."""
from ursina import application

from . import settings
from .world import ASSETS

_music = None


def start():
    """Load and loop the track once; later calls only re-apply the volume."""
    global _music
    if _music is None:
        path = ASSETS / 'tetris.mp3'
        if not path.exists():
            return
        from panda3d.core import Filename
        _music = application.base.loader.loadMusic(Filename.fromOsSpecific(str(path)))
        if _music is None:
            return
        _music.setLoop(True)
        _music.play()
        settings.on_change(lambda key, value: key == 'music' and set_volume(value))
    set_volume(settings.get('music'))


def set_volume(value):
    if _music is not None:
        _music.setVolume(max(0.0, min(1.0, value)) * 0.5)    # full slider is loud enough at half gain
