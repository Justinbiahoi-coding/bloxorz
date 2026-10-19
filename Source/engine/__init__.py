"""Public engine API.

Nothing in this package imports pygame. A UI layer should depend only on the
names exported here (and on plain Python data) so it can be replaced.
"""
from .level import Level
from .problem import Bloxorz, State
from .session import GameSession
from .solver import (ALGORITHM_NAMES, SolveResult, solve, solve_problem)

__all__ = [
    'Level',
    'Bloxorz',
    'State',
    'GameSession',
    'ALGORITHM_NAMES',
    'SolveResult',
    'solve',
    'solve_problem',
]
