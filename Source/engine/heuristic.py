"""Point relaxation: all potential floor, open bridges and directed teleports."""
from collections import deque
from math import inf


def board_key(level, goal):
    """Immutable topology/goal key, independent of the current initial state."""
    return (frozenset(level.kinds),
            frozenset((cell, tuple(targets)) for cell, targets in level.splits.items()),
            tuple(goal.position))


def relaxed_distances(key):
    """Distances TO the goal, using 0-1 BFS on the reversed point graph.

    All orthogonal floor edges cost 1. A real teleport trigger -> target is
    reversed as target -> trigger with cost 0, never the opposite direction.
    Unreachable cells retain infinity, rather than being assigned zero.
    """
    cells, splits, goal = key
    reverse = {cell: [] for cell in cells}
    for x, y in cells:
        for dx, dy in ((0, 1), (0, -1), (-1, 0), (1, 0)):
            neighbor = (x + dx, y + dy)
            if neighbor in cells:
                reverse[neighbor].append(((x, y), 1))
    for trigger, targets in splits:
        for target in zip(targets[::2], targets[1::2]):
            reverse[target].append((trigger, 0))

    distances = dict.fromkeys(cells, inf)
    distances[goal] = 0
    queue = deque([goal])
    while queue:
        cell = queue.popleft()
        for predecessor, weight in reverse[cell]:
            candidate = distances[cell] + weight
            if candidate < distances[predecessor]:
                distances[predecessor] = candidate
                if weight:
                    queue.append(predecessor)
                else:
                    queue.appendleft(predecessor)
    return distances
