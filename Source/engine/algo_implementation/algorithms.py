from collections import deque
import time

from .node import Node


def depth_first_graph_search(problem):
    raise NotImplementedError


def breadth_first_graph_search(problem):
    """Return the shortest path in steps, expanded nodes, and search time."""
    started_at = time.perf_counter()
    root = Node(problem.initial)
    frontier = deque([root])
    discovered = {root.state}
    explored_ordered = []

    while frontier:
        node = frontier.popleft()
        if problem.goal_test(node.state):
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return [node, explored_ordered, elapsed_ms]

        explored_ordered.append(node)
        for child in node.expand(problem):
            if child.state not in discovered:
                discovered.add(child.state)
                frontier.append(child)

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return [None, explored_ordered, elapsed_ms]


def depth_limited_search(problem, limit=50):
    raise NotImplementedError


def iterative_deepening_search(problem):
    raise NotImplementedError


def uniform_cost_search(problem):
    raise NotImplementedError


def bidirectional_search(problem):
    raise NotImplementedError


def astar_search(problem, h):
    raise NotImplementedError
