import json
from pathlib import Path

""" Level: represents a game level from Roll the Block """

BASE_DIR = Path(__file__).resolve().parent.parent


class Level:
    def __init__(self, level_number):
        self.load_level(BASE_DIR / 'levels' / '{}.json'.format(level_number))

    def load_level(self, path_to_level):
        with open(path_to_level, "r", encoding="utf-8") as level_file:
            json_obj = json.load(level_file)

        self.map = json_obj["map"]
        self.level = json_obj["level"]
        self.size = json_obj["size"]

        self.start = list(json_obj["start"])
        self.start.reverse()

        self.end = list(json_obj["end"])
        self.end.reverse()

    def is_tile_available(self, x, y):
        return (0 <= x < self.size and 0 <= y < self.size
                and self.map[y][x] == 1)
