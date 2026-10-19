"""UI-independent game session.

This is the seam a new UI can build on: it exposes the current state, legal
moves, move count, win status and hints without importing pygame.
"""
from .problem import Bloxorz
from .solver import solve_problem


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
        """Tile kind at column x, row y: 'floor', 'void' or 'goal'."""
        if [x, y] == list(self.goal.position):
            return 'goal'
        return 'floor' if self.level.is_tile_available(x, y) else 'void'

    def block_cells(self, state=None):
        """Cells (x, y) the block occupies in ``state`` (default: current)."""
        p = (state or self.state).position
        return [(p[i], p[i + 1]) for i in range(0, len(p), 2)]

    def actions(self):
        return self.problem.actions(self.state)

    def move(self, action):
        """Apply a move. Returns True if the state changed."""
        if self.won:
            return False

        new_state = self.problem.do_action_if_possible(self.state, action)
        if new_state is None:
            return False

        self.state = new_state
        self.moves += 1
        self.hint = None
        return True

    def set_state(self, state, increment_moves=True):
        """Set the state directly; used by solution playback views."""
        if self.state.position != state.position:
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
