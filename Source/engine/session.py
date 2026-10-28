"""UI-independent game session.

This is the seam a new UI can build on: it exposes the current state, legal
moves, move count, win status and hints without importing pygame.
"""
from .problem import Bloxorz
from .solver import solve_problem


_TILE_NAMES = {'b': 'floor', 'e': 'goal', 'f': 'fragile', 's': 'soft', 'h': 'heavy', 'v': 'split'}


class GameSession:
    def __init__(self, level_number):
        self.problem = Bloxorz(level_number)
        self.level = self.problem.level
        self.goal = self.problem.goal
        self.level_number = level_number
        self.reset()

    def reset(self):
        self.state = self.problem.initial
        self.moves = 0
        self.hint = None

    @property
    def won(self):
        return self.problem.goal_test(self.state)

    def tile_at(self, x, y):
        """Tile kind at column x, row y, given the current bridge states."""
        kind = self.level.kinds.get((x, y))
        if kind is None:
            return 'void'
        if kind in 'lrkq':
            return 'bridge_open' if self.state.bridges[self.level.bridge_index[(x, y)]] else 'bridge_closed'
        return _TILE_NAMES[kind]

    def block_cells(self, state=None):
        """Cells (x, y) the block occupies in ``state`` (default: current); split cubes are two apart cells."""
        p = (state or self.state).position
        return [(p[i], p[i + 1]) for i in range(0, len(p), 2)]

    @property
    def is_split(self):
        return self.state.split

    @property
    def active(self):
        return self.state.active

    def actions(self):
        return self.problem.actions(self.state)

    def attempt_move(self, action):
        """Apply a move and report whether it succeeded, won, or left the board."""
        if self.won:
            return 'blocked', self.state, self.state

        before = self.state
        new_state = self.problem.do_action_if_possible(before, action)
        if new_state is None:
            return 'fell', before, before

        self.state = new_state
        self.moves += 1
        self.hint = None
        status = 'won' if self.problem.goal_test(new_state) else 'moved'
        return status, before, new_state

    def move(self, action):
        """Apply a move. Returns True if the state changed."""
        return self.attempt_move(action)[0] in ('moved', 'won')

    def set_state(self, state, increment_moves=True):
        """Set the state directly; used by solution playback views."""
        if self.state != state:
            self.state = state
            if increment_moves:
                self.moves += 1

    def request_hint(self):
        """Compute and cache the next state towards a solution."""
        if self.won:
            return None

        result = solve_problem(
            self.problem, 'Uniform Cost Search', initial=self.state)
        if not result.solved:
            self.hint = None
            return None

        path = result.solution_path()
        self.hint = path[1] if len(path) > 1 else path[0]
        return self.hint
