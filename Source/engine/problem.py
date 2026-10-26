from .algo_implementation.problem import Problem
from .level import BRIDGE, Level

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
            return State(state.position, state.bridges, True, 1 - state.active)
        return self._move(state, action)

    def do_action_if_possible(self, state, action):
        if action in self.actions(state):
            return self.result(state, action)
        return None

    def goal_test(self, state):
        # the block must stand upright on the goal; split cubes never win
        return not state.split and state.position == self.goal.position

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

        if any(not self._floor(c, state.bridges) for c in piece):
            return None
        if standing and self.level.kinds[piece[0]] == 'f':   # fragile breaks under a standing block
            return None

        bridges = list(state.bridges)
        split_to = None
        for c in piece:
            kind = self.level.kinds[c]
            if kind == 's' or (kind == 'h' and standing):
                for bx, by, mode in self.level.switches.get(c, ()):
                    i = self.level.bridge_index[(bx, by)]
                    bridges[i] = {'onoff': 1 - bridges[i], 'on': 1, 'off': 0}[mode]
            elif kind == 'v' and standing:
                split_to = self.level.splits[c]
        bridges = tuple(bridges)

        if split_to:
            cubes = [tuple(split_to[:2]), tuple(split_to[2:])]
            if any(not self._floor(c, bridges) for c in cubes):
                return None
            return State(list(split_to), bridges, True, 0)

        if state.split:
            cubes = list(cells)
            cubes[state.active] = piece[0]
            if cubes[0] == cubes[1]:
                return None
            if any(not self._floor(c, bridges) for c in cubes):
                return None
            (ax, ay), (bx, by) = cubes
            if abs(ax - bx) + abs(ay - by) == 1:            # adjacent cubes merge back into a block
                return State(_flat(sorted(cubes)), bridges)
            return State(_flat(cubes), bridges, True, state.active)

        if any(not self._floor(c, bridges) for c in piece):  # a bridge closed under the block
            return None
        return State(_flat(sorted(piece)), bridges)

    ## Manhattan distance based heuristic.
    def h1(self, node):
        if node.state.split:
            return 0   # ponytail: trivially admissible; a real split heuristic is future work
        [x_goal, y_goal] = self.goal.position

        if len(node.state.position) == 2:
            [x_block, y_block] = node.state.position
        else:
            # Select position of the block nearest to the goal.
            [block_pos_x1, block_pos_y1, block_pos_x2, block_pos_y2] = node.state.position
            [x_block, y_block] = self.closest_point(x_goal, y_goal, block_pos_x1, block_pos_y1, block_pos_x2, block_pos_y2)

        return (abs(x_goal - x_block) + abs(y_goal - y_block)) // 2

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
