import time

from .node import Node
from .utils import PriorityQueue


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


def breadth_first_graph_search(problem):
    raise NotImplementedError


def depth_limited_search(problem, limit=50):
    raise NotImplementedError


def iterative_deepening_search(problem):
    raise NotImplementedError


def uniform_cost_search(problem):
    raise NotImplementedError


def bidirectional_search(problem):
    raise NotImplementedError


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
