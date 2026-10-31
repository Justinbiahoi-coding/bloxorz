from collections import deque
import heapq
from itertools import count
import time

from .node import Node
from .utils import PriorityQueue
from ..search_model import rolling_search


@rolling_search
def depth_first_graph_search(problem):
    """Graph-search DFS with visited-set duplicate detection.

    Returns [goal_node | None, explored_ordered, elapsed_ms].

    Uses a LIFO stack for the frontier and a set of already-expanded
    states to avoid infinite loops in cyclic state spaces.
    Does NOT guarantee an optimal solution.
    """
    start_time = time.perf_counter()

    node = Node(problem.initial)

    frontier = [node]                # LIFO stack
    explored = set()
    explored_ordered = []

    while frontier:
        node = frontier.pop()

        if node.state in explored:
            continue

        explored.add(node.state)
        explored_ordered.append(node.state)

        if problem.goal_test(node.state):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return [node, explored_ordered, elapsed_ms]

        for child in node.expand(problem):
            if child.state not in explored:
                frontier.append(child)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return [None, explored_ordered, elapsed_ms]


@rolling_search
def breadth_first_graph_search(problem):
    """Shortest edge/roll path, valid pops including the goal, and search time."""
    started_at = time.perf_counter()
    root = Node(problem.initial)
    frontier = deque([root])
    discovered = {root.state}
    explored_ordered = []

    while frontier:
        node = frontier.popleft()
        explored_ordered.append(node)
        if problem.goal_test(node.state):
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return [node, explored_ordered, elapsed_ms]

        for child in node.expand(problem):
            if child.state not in discovered:
                discovered.add(child.state)
                frontier.append(child)

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return [None, explored_ordered, elapsed_ms]


def depth_limited_search(problem, limit=50):
    raise NotImplementedError


@rolling_search
def uniform_cost_search(problem):
    """Find a minimum-cost path when all step costs are nonnegative."""
    started_at = time.perf_counter()
    root = Node(problem.initial)
    order = count()
    frontier = [(root.path_cost, next(order), root)]
    best_cost = {root.state: root.path_cost}
    explored_ordered = []

    while frontier:
        _, _, node = heapq.heappop(frontier)
        if node.path_cost != best_cost[node.state]:
            continue
        explored_ordered.append(node)
        if problem.goal_test(node.state):
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return [node, explored_ordered, elapsed_ms]

        for child in node.expand(problem):
            if (child.state not in best_cost
                    or child.path_cost < best_cost[child.state]):
                best_cost[child.state] = child.path_cost
                heapq.heappush(frontier, (child.path_cost, next(order), child))

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    return [None, explored_ordered, elapsed_ms]


def bidirectional_search(problem):
    raise NotImplementedError


@rolling_search
def astar_search(problem, h):
    """A* graph search with lazy duplicate detection.

    Returns [goal_node | None, explored_ordered, elapsed_ms].

    Guarantees an optimal solution when *h* is admissible.  Uses a
    min-priority queue ordered by f(n) = g(n) + h(n) and tracks the
    best known g-cost per state so stale frontier entries are discarded
    on pop rather than requiring an expensive decrease-key operation.

    Parameters
    ----------
    problem : Problem
        Must provide actions, result, goal_test, path_cost.
    h : callable(Node) -> number
        Heuristic estimating remaining cost from a node to the goal.
    """
    start_time = time.perf_counter()

    f = lambda n: n.path_cost + h(n)
    node = Node(problem.initial)

    frontier = PriorityQueue(order='min', f=f)
    frontier.append(node)

    # Best known g-cost for each state (enables lazy deletion).
    best_g = {node.state: 0}
    explored_ordered = []

    while len(frontier) > 0:
        node = frontier.pop()

        # Discard stale entry: a cheaper path was already expanded.
        if node.path_cost > best_g.get(node.state, float('inf')):
            continue

        explored_ordered.append(node.state)

        # Goal check on expansion (guarantees optimality with admissible heuristic).
        if problem.goal_test(node.state):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return [node, explored_ordered, elapsed_ms]

        for child in node.expand(problem):
            child_cost = child.path_cost
            if child_cost < best_g.get(child.state, float('inf')):
                best_g[child.state] = child_cost
                frontier.append(child)

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return [None, explored_ordered, elapsed_ms]
