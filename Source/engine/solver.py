"""Search algorithm facade for the engine layer.

The UI should not need to know which search function backs each algorithm.
"""
import tracemalloc
from dataclasses import dataclass

from .problem import Bloxorz
from .algo_implementation.algorithms import (depth_first_graph_search,
                              breadth_first_graph_search,
                              iterative_deepening_search,
                              uniform_cost_search,
                              astar_search)

ALGORITHM_NAMES = (
    'DFS',
    'BFS',
    'Iterative DFS',
    'Uniform Cost Search',
    'A*',
)


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
        return len(self.explored)

    @property
    def solution_length(self):
        """Number of moves in the solution, or None."""
        path = self.solution_path()
        return None if path is None else len(path) - 1

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


def _iterative_deepening(problem):
    return iterative_deepening_search(problem)


def _uniform_cost(problem):
    return uniform_cost_search(problem)


def _astar(problem):
    return astar_search(problem, problem.h1)


_ALGORITHMS = {
    'DFS': _depth_first,
    'BFS': _breadth_first,
    'Iterative DFS': _iterative_deepening,
    'Uniform Cost Search': _uniform_cost,
    'A*': _astar,
}


def _peak_memory_kb(runner, problem):
    """Peak memory the search allocates, in KB, measured with tracemalloc."""
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
