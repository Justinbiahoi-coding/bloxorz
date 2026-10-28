import json
from pathlib import Path

""" Level: a stage loaded from levels/<n>.json.

Two formats. Plain: "map" is a 0/1 grid and "end" is the goal. Advanced: "tiles" is a grid of
characters, plus optional "switches" and "splits". Tile characters:
  b floor   e goal   f fragile   s soft switch   h heavy switch   v split tile
  l, r closed bridge   k, q open bridge   (space) void
"start" and "end" are [row, col]; positions inside the engine are (x, y) = (col, row).
"""

BASE_DIR = Path(__file__).resolve().parent.parent
FLOOR = set('bsehvf')   # solid whatever the bridge state
BRIDGE = set('lrkq')
TILES = FLOOR | BRIDGE
SWITCH_MODES = {'onoff', 'on', 'off'}


class Level:
    def __init__(self, level_number):
        self.load_level(BASE_DIR / 'levels' / '{}.json'.format(level_number))

    def load_level(self, path_to_level):
        with open(path_to_level, "r", encoding="utf-8") as level_file:
            json_obj = json.load(level_file)

        self.level = json_obj["level"]
        self.size = json_obj["size"]
        self.start = list(json_obj["start"])[::-1]
        self.end = list(json_obj["end"])[::-1]

        if not isinstance(self.size, int) or self.size <= 0:
            raise ValueError('invalid board size: {}'.format(self.size))

        if "tiles" in json_obj:
            rows = json_obj["tiles"]
            if len(rows) != self.size:
                raise ValueError('tiles must have {} rows'.format(self.size))
            self.kinds = {}
            for y, row in enumerate(rows):
                if len(row) != self.size:
                    raise ValueError('tile row {} must have {} columns'.format(y, self.size))
                for x, ch in enumerate(row):
                    if ch == ' ':
                        continue
                    if ch not in TILES:
                        raise ValueError('unknown tile {!r} at ({}, {})'.format(ch, x, y))
                    self.kinds[(x, y)] = ch
        else:
            rows = json_obj["map"]
            if len(rows) != self.size:
                raise ValueError('map must have {} rows'.format(self.size))
            self.kinds = {}
            for y, row in enumerate(rows):
                if len(row) != self.size:
                    raise ValueError('map row {} must have {} columns'.format(y, self.size))
                for x, value in enumerate(row):
                    if value:
                        self.kinds[(x, y)] = 'b'

        for name, cell in (('start', self.start), ('end', self.end)):
            if not (0 <= cell[0] < self.size and 0 <= cell[1] < self.size):
                raise ValueError('{} is outside the board: {}'.format(name, cell))

        if "tiles" in json_obj:
            if self.kinds.get(tuple(self.end)) != 'e':
                raise ValueError('end must be a goal tile')
        else:
            if tuple(self.end) not in self.kinds:
                raise ValueError('end must be on the map')
            self.kinds[tuple(self.end)] = 'e'

        start_kind = self.kinds.get(tuple(self.start))
        if start_kind not in FLOOR or start_kind == 'f':
            raise ValueError('start must be on a solid, non-fragile tile')

        self.map = [[1 if (x, y) in self.kinds else 0 for x in range(self.size)]
                    for y in range(self.size)]

        cells = sorted((c for c, ch in self.kinds.items() if ch in BRIDGE),
                       key=lambda c: (c[1], c[0]))
        self.bridge_index = {c: i for i, c in enumerate(cells)}
        self.bridges_open = tuple(1 if self.kinds[c] in 'kq' else 0 for c in cells)

        self.switches = {}
        for item in json_obj.get("switches", []):
            at = tuple(item["at"])
            if self.kinds.get(at) not in ('s', 'h'):
                raise ValueError('switch must be on a soft or heavy switch tile: {}'.format(at))
            if at in self.switches:
                raise ValueError('duplicate switch at {}'.format(at))
            links = []
            for bridge in item["bridges"]:
                if len(bridge) != 3:
                    raise ValueError('switch bridge entries need x, y, and mode')
                bx, by, mode = bridge
                if (bx, by) not in self.bridge_index:
                    raise ValueError('switch links to a missing bridge: ({}, {})'.format(bx, by))
                if mode not in SWITCH_MODES:
                    raise ValueError('unknown switch mode: {!r}'.format(mode))
                links.append((bx, by, mode))
            self.switches[at] = links

        self.splits = {}
        for item in json_obj.get("splits", []):
            at = tuple(item["at"])
            if self.kinds.get(at) != 'v':
                raise ValueError('split switch must be on a split tile: {}'.format(at))
            if at in self.splits:
                raise ValueError('duplicate split switch at {}'.format(at))
            cubes = list(item["cubes"])
            if len(cubes) != 4:
                raise ValueError('split switch needs two cube coordinates')
            a, b = (cubes[0], cubes[1]), (cubes[2], cubes[3])
            if a == b:
                raise ValueError('split cubes must occupy different cells')
            if any(cell not in self.kinds for cell in (a, b)):
                raise ValueError('split cube target is outside the tiles')
            self.splits[at] = cubes

        for cell, kind in self.kinds.items():
            if kind in 'sh' and cell not in self.switches:
                raise ValueError('switch tile without configuration: {}'.format(cell))
            if kind == 'v' and cell not in self.splits:
                raise ValueError('split tile without configuration: {}'.format(cell))

    def is_tile_available(self, x, y):
        """True for tiles that are solid regardless of bridge state."""
        return self.kinds.get((x, y)) in FLOOR
