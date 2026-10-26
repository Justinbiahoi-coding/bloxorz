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

        if "tiles" in json_obj:
            rows = json_obj["tiles"]
            self.kinds = {(x, y): ch for y, row in enumerate(rows)
                          for x, ch in enumerate(row) if ch != ' '}
        else:
            self.kinds = {(x, y): 'b' for y, row in enumerate(json_obj["map"])
                          for x, v in enumerate(row) if v}
            self.kinds[tuple(self.end)] = 'e'
        self.map = [[1 if (x, y) in self.kinds else 0 for x in range(self.size)]
                    for y in range(self.size)]

        cells = sorted((c for c, ch in self.kinds.items() if ch in BRIDGE),
                       key=lambda c: (c[1], c[0]))
        self.bridge_index = {c: i for i, c in enumerate(cells)}
        self.bridges_open = tuple(1 if self.kinds[c] in 'kq' else 0 for c in cells)
        self.switches = {tuple(s["at"]): [tuple(b) for b in s["bridges"]]
                         for s in json_obj.get("switches", [])}
        self.splits = {tuple(s["at"]): list(s["cubes"])
                       for s in json_obj.get("splits", [])}

    def is_tile_available(self, x, y):
        """True for tiles that are solid regardless of bridge state."""
        return self.kinds.get((x, y)) in FLOOR
