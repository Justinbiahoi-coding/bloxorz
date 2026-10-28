"""Player settings and Free Play progress, kept in Source/settings.json between runs.

A missing, unreadable or read-only file never stops the game: defaults are used and saving is skipped.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / 'settings.json'

DEFAULTS = {
    'music': 0.4,           # 0..1
    'fullscreen': False,
    'key_hints': True,      # the key chips along the bottom of every screen
    'legend': True,         # the tile legend in game
    'move_speed': 1.0,      # how fast the block rolls (and solutions replay)
    'completed': [],        # Free Play levels finished at least once
}

SPEEDS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0)

_values = dict(DEFAULTS)
_listeners = []


def load():
    try:
        data = json.loads(PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    for key, default in DEFAULTS.items():
        value = data.get(key)
        if isinstance(default, bool):
            ok = isinstance(value, bool)
        elif isinstance(default, float):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            ok = isinstance(value, type(default))
        if ok:
            _values[key] = value


def save():
    try:
        PATH.write_text(json.dumps(_values, indent=2), encoding='utf-8')
    except OSError:
        pass


def get(key):
    return _values[key]


def set(key, value):
    _values[key] = value
    save()
    for fn in list(_listeners):
        fn(key, value)


def on_change(fn):
    """Call fn(key, value) whenever a setting changes."""
    _listeners.append(fn)


def off(fn):
    if fn in _listeners:
        _listeners.remove(fn)


def mark_completed(level_number):
    done = _values['completed']
    if level_number not in done:
        set('completed', sorted(done + [level_number]))


def is_completed(level_number):
    return level_number in _values['completed']
