"""Search algorithm facade for the engine layer.

The UI should not need to know which search function backs each algorithm.
"""
import tracemalloc
from dataclasses import dataclass

from .problem import Bloxorz
from .algo_implementation.algorithms import (depth_first_graph_search,
                              breadth_first_graph_search,
                              uniform_cost_search,
                              astar_search)

# Supported algorithms, in display order, shared by both UIs.
ALGORITHM_NAMES = (
    'BFS',
    'DFS',
    'Uniform Cost Search',
    'A*',
)


def count_moves(actions):
    """Count non-SWITCH actions, including arbitrary labels in generic problems."""
    return sum(action != 'SWITCH' for action in actions)


@dataclass
class SolveResult:
    algorithm: str
    level_number: int
    goal_node: object
    explored: list
    elapsed_ms: float
    peak_memory_kb: float = None   # None when the run was not measured

    @property
    def solved(self):
        return self.goal_node is not None

    @property
    def expanded(self):
        """Valid frontier pops, including the goal; a reopened state counts again."""
        return len(self.explored)

    @property
    def solution_length(self):
        """MOVES: number of non-SWITCH actions, or None when unsolved."""
        if self.goal_node is None:
            return None
        return count_moves(self.goal_node.solution())

    @property
    def action_count(self):
        """Number of replay/search actions, including SWITCH, or None."""
        return None if self.goal_node is None else len(self.goal_node.solution())

    @property
    def solution_cost(self):
        if self.goal_node is None:
            return None
        return self.goal_node.path_cost

    def solution_path(self):
        if self.goal_node is None:
            return None
        return self.goal_node.path()


def _depth_first(problem):
    return depth_first_graph_search(problem)


def _breadth_first(problem):
    return breadth_first_graph_search(problem)


def _uniform_cost(problem):
    return uniform_cost_search(problem)


def _astar(problem):
    return astar_search(problem, problem.h1)


_ALGORITHMS = {
    'DFS': _depth_first,
    'BFS': _breadth_first,
    'Uniform Cost Search': _uniform_cost,
    'A*': _astar,
}


def _peak_memory_kb(runner, problem):
    """Peak traced allocation above baseline, including a fresh heuristic table."""
    owner = not tracemalloc.is_tracing()
    if owner:
        tracemalloc.start()
    tracemalloc.reset_peak()
    before = tracemalloc.get_traced_memory()[0]
    try:
        runner(problem)
        return (tracemalloc.get_traced_memory()[1] - before) / 1024
    finally:
        if owner:
            tracemalloc.stop()


def solve_problem(problem, algorithm, initial=None, measure_memory=False):
    """Run a search algorithm against an existing problem.

    ``initial`` optionally overrides the start state, which is useful for hints.
    The original problem state is restored afterwards.
    ``measure_memory`` runs the search a second time under tracemalloc to fill in
    ``peak_memory_kb``; tracing slows the search, so the timing comes from the first run.
    Each Bloxorz run resets its heuristic table inside the measured search.
    Time and memory include graph/table construction and primitive Node conversion,
    but exclude loading the level and GUI/replay work.
    """
    try:
        runner = _ALGORITHMS[algorithm]
    except KeyError:
        raise ValueError('Unknown algorithm: {}'.format(algorithm))

    original_initial = problem.initial
    if initial is not None:
        problem.initial = initial
    try:
        goal_node, explored, elapsed_ms = runner(problem)
        peak = _peak_memory_kb(runner, problem) if measure_memory else None
    finally:
        problem.initial = original_initial

    level_number = getattr(problem.level, 'level', None)
    return SolveResult(algorithm, level_number, goal_node, explored, elapsed_ms, peak)


def solve(level_number, algorithm, measure_memory=True):
    """Solve a level using the requested algorithm, with all four metrics."""
    return solve_problem(Bloxorz(level_number), algorithm, measure_memory=measure_memory)
