from math import inf

from .algo_implementation.problem import Problem
from .level import BRIDGE, Level
from .heuristic import board_key, relaxed_distances

DIRS = {'UP': (0, 1), 'DOWN': (0, -1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}


class Bloxorz(Problem):

    def __init__(self, map_number):
        self.level = Level(map_number)
        initial = State(self.level.start, self.level.bridges_open)
        goal = State(self.level.end)
        Problem.__init__(self, initial, goal)

    def new_possible_states(self, state):
        return [self.result(state, action) for action in self.actions(state)]

    def actions(self, state):
        actions = [a for a in DIRS if self._move(state, a) is not None]
        if state.split:
            actions.append('SWITCH')   # change which cube is controlled
        return actions

    def result(self, state, action):
        if action == 'SWITCH':
            if not state.split:
                return None
            return State(state.position, state.bridges, True, 1 - state.active)
        return self._move(state, action)

    def do_action_if_possible(self, state, action):
        if action in self.actions(state):
            return self.result(state, action)
        return None

    def goal_test(self, state):
        # the block must stand upright on the goal; split cubes never win
        return not state.split and state.position == self.goal.position

    def path_cost(self, c, state1, action, state2):
        """Base cost 1, plus 2 once if the moved part lands on fragile tiles.

        Whole-block moves include both destinations after a split/teleport.
        For a split-cube move, exclude the stationary cube by its old cell,
        including when the output coordinates have been sorted by merging.
        """
        if action == 'SWITCH':
            return c + 1

        landed = zip(state2.position[::2], state2.position[1::2])
        if state1.split:
            index = 2 * (1 - state1.active)
            stationary = tuple(state1.position[index:index + 2])
            landed = (cell for cell in landed if cell != stationary)

        surcharge = 2 if any(self.level.kinds.get(cell) == 'f' for cell in landed) else 0
        return c + 1 + surcharge

    def _floor(self, cell, bridges):
        kind = self.level.kinds.get(cell)
        if kind is None:
            return False
        if kind in BRIDGE:
            return bool(bridges[self.level.bridge_index[cell]])
        return True

    def _move(self, state, action):
        """Next State after rolling (the active cube of) the block, or None if illegal."""
        dx, dy = DIRS[action]
        p = state.position
        cells = [(p[i], p[i + 1]) for i in range(0, len(p), 2)]
        if state.split:
            piece = [(cells[state.active][0] + dx, cells[state.active][1] + dy)]
        else:
            piece = _roll(cells, dx, dy)
        standing = not state.split and len(piece) == 1

        bridges = list(state.bridges)
        split_to = None
        for c in piece:
            kind = self.level.kinds.get(c)
            if kind == 's' or (kind == 'h' and standing):
                for bx, by, mode in self.level.switches.get(c, ()):
                    i = self.level.bridge_index[(bx, by)]
                    bridges[i] = {'onoff': 1 - bridges[i], 'on': 1, 'off': 0}[mode]
            elif kind == 'v' and standing:
                split_to = self.level.splits[c]
        bridges = tuple(bridges)

        if split_to:
            cubes = [tuple(split_to[:2]), tuple(split_to[2:])]
            if cubes[0] == cubes[1]:
                return None
            if any(not self._floor(c, bridges) for c in cubes):
                return None
            if _adjacent(cubes[0], cubes[1]):
                return State(_flat(sorted(cubes)), bridges)
            return State(list(split_to), bridges, True, 0)

        if state.split:
            cubes = list(cells)
            cubes[state.active] = piece[0]
            if cubes[0] == cubes[1]:
                return None
            if any(not self._floor(c, bridges) for c in cubes):
                return None
            if _adjacent(cubes[0], cubes[1]):                # adjacent cubes merge back into a block
                return State(_flat(sorted(cubes)), bridges)
            return State(_flat(cubes), bridges, True, state.active)

        if any(not self._floor(c, bridges) for c in piece):  # a bridge closed under the block
            return None
        if standing and self.level.kinds.get(piece[0]) == 'f':   # fragile breaks under a standing block
            return None
        return State(_flat(sorted(piece)), bridges)

    def reset_heuristic_cache(self):
        """Each search, including the traced run, builds its own distance table."""
        self._relaxed_cache = None

    def h1(self, node):
        """ceil(min relaxed point distance / 2), for every block configuration."""
        key = board_key(self.level, self.goal)
        cache = getattr(self, '_relaxed_cache', None)
        if cache is None or cache[0] != key:
            cache = self._relaxed_cache = (key, relaxed_distances(key))
        position = node.state.position
        distance = min(cache[1].get(cell, inf)
                       for cell in zip(position[::2], position[1::2]))
        return inf if distance == inf else (distance + 1) // 2

    # Returns the closest point to the goal based on the manhattam distance
    def closest_point(self, x_goal, y_goal, x1, y1, x2, y2):
        distance_1 = abs(x_goal - x1) + abs(y_goal - y1)
        distance_2 = abs(x_goal - x2) + abs(y_goal - y2)
        if distance_1 > distance_2:
            return [x2, y2]
        else:
            return [x1, y1]


def _flat(cells):
    return [v for c in cells for v in c]


def _adjacent(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def _roll(cells, dx, dy):
    """Cells covered by the block after rolling it by (dx, dy)."""
    if len(cells) == 1:                                       # standing: tips over
        (x, y), = cells
        return [(x + dx, y + dy), (x + 2 * dx, y + 2 * dy)]
    (x1, y1), (x2, y2) = cells
    if (x2 - x1, y2 - y1) in ((dx, dy), (-dx, -dy)):          # lying along the move: stands up
        fx, fy = max(cells, key=lambda c: c[0] * dx + c[1] * dy)
        return [(fx + dx, fy + dy)]
    return [(x1 + dx, y1 + dy), (x2 + dx, y2 + dy)]           # lying across: rolls sideways


# Custom state for Bloxorz. position: [x, y] standing, [x1, y1, x2, y2] lying (sorted) or two split cubes.
# bridges: open(1)/closed(0) flag per bridge; split/active: split-cube mode and which cube is controlled.
class State():
    def __init__(self, position, bridges=(), split=False, active=0):
        self.position = position
        self.bridges = tuple(bridges)
        self.split = split
        self.active = active

    def _key(self):
        return (tuple(self.position), self.bridges, self.split, self.active)

    def __hash__(self):
        return hash(self._key())

    def __eq__(self, other):
        return isinstance(other, State) and self._key() == other._key()

    def __lt__(self, node):
        return self._key() < node._key()
