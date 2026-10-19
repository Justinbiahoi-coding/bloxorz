"""Search algorithm facade for the engine layer.

The UI should not need to know which search function backs each algorithm.
"""
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

    @property
    def solved(self):
        return self.goal_node is not None

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


def solve_problem(problem, algorithm, initial=None):
    """Run a search algorithm against an existing problem.

    ``initial`` optionally overrides the start state, which is useful for hints.
    The original problem state is restored afterwards.
    """
    try:
        runner = _ALGORITHMS[algorithm]
    except KeyError:
        raise ValueError('Unknown algorithm: {}'.format(algorithm))

    if initial is not None:
        original_initial = problem.initial
        problem.initial = initial
        try:
            goal_node, explored, elapsed_ms = runner(problem)
        finally:
            problem.initial = original_initial
    else:
        goal_node, explored, elapsed_ms = runner(problem)

    level_number = getattr(problem.level, 'level', None)
    return SolveResult(algorithm, level_number, goal_node, explored, elapsed_ms)


def solve(level_number, algorithm):
    """Solve a level using the requested algorithm."""
    return solve_problem(Bloxorz(level_number), algorithm)
