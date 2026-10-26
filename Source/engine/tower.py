"""A tower: consecutive floors, each one a level. Winning a floor drops the block onto the next."""
from .session import GameSession

# Level numbers, top floor first; teaches plain rolling, then split, bridges/switches, fragile tiles.
FLOORS = (2, 3, 21, 13, 28, 22, 14, 29, 24, 25)


class Tower:
    def __init__(self, floors=FLOORS):
        self.floors = tuple(floors)
        self.index = 0
        self.total_moves = 0          # moves on floors already finished
        self.session = GameSession(self.floors[0])

    @property
    def count(self):
        return len(self.floors)

    @property
    def is_last(self):
        return self.index == self.count - 1

    def descend(self):
        """Move to the next floor once the current one is won. False on the last floor."""
        if not self.session.won or self.is_last:
            return False
        self.total_moves += self.session.moves
        self.index += 1
        self.session = GameSession(self.floors[self.index])
        return True
