"""Level catalog shared by the 2D and 3D front-ends."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LEVEL_DIR = BASE_DIR / 'levels'
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


def _discover_levels():
    return sorted(int(path.stem) for path in LEVEL_DIR.glob('*.json'))


def has_advanced_tiles(level_number):
    try:
        data = json.loads((LEVEL_DIR / '{}.json'.format(level_number)).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    return bool(set(''.join(data.get('tiles', []))) & ADVANCED_TILES)


def level_label(level_number):
    return TUTORIAL_NAMES.get(level_number, 'Level {}'.format(level_number))


LAST_NORMAL_LEVEL = 23       # Normal: the four tutorials, then levels 1-23. Advanced: level 24 and up.
LEVEL_NUMBERS = _discover_levels()
_TUTORIALS = [number for number in TUTORIAL_LEVELS if number in LEVEL_NUMBERS]
_REGULAR = [number for number in LEVEL_NUMBERS if number not in _TUTORIALS]
NORMAL_LEVELS = _TUTORIALS + [number for number in _REGULAR if number <= LAST_NORMAL_LEVEL]
ADVANCED_LEVELS = [number for number in _REGULAR if number > LAST_NORMAL_LEVEL]


def levels_for_mode(mode):
    return list(ADVANCED_LEVELS if mode == 'advanced' else NORMAL_LEVELS)


def next_level(mode, level_number):
    levels = levels_for_mode(mode)
    try:
        index = levels.index(level_number)
    except ValueError:
        return None
    return levels[index + 1] if index + 1 < len(levels) else None
