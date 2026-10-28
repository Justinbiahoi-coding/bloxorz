# Bloxorz Solver Implementation Guide

This document is for the member implementing the search algorithms. The
algorithm functions in `Source/engine/algo_implementation/algorithms.py` are
currently placeholders. The problem, level, state, node, solver facade, session,
and UI are implemented and should not be duplicated.

Read also:

- [`ALGORITHM_IMPLEMENTATION_GUIDE.md`](ALGORITHM_IMPLEMENTATION_GUIDE.md) for
  the state, level, and problem interface.
- [`ADVANCED_MECHANICS.md`](ADVANCED_MECHANICS.md) for fragile tiles, bridges,
  switches, and split-cube rules.

## 1. Files and responsibilities

| File | Responsibility |
| --- | --- |
| `Source/engine/algo_implementation/algorithms.py` | Search algorithm implementations; currently placeholders |
| `Source/engine/algo_implementation/node.py` | Search-tree `Node` |
| `Source/engine/algo_implementation/problem.py` | Generic abstract `Problem` |
| `Source/engine/problem.py` | Bloxorz `State`, transitions, goal test, heuristic |
| `Source/engine/level.py` | Level JSON loading and validation |
| `Source/engine/solver.py` | Algorithm dispatch and `SolveResult` |
| `Source/ui/algorithm_views.py` | Runs the selected solver and displays metrics/results |
| `Source/tests/test_logic.py` | Solver-facing tests |
| `Source/tests/test_advanced.py` | Advanced-mechanic reference BFS tests |

## 2. Required functions

The solver facade imports these names from
`Source/engine/algo_implementation/algorithms.py`:

```python
depth_first_graph_search(problem)
breadth_first_graph_search(problem)
iterative_deepening_search(problem)
uniform_cost_search(problem)
astar_search(problem, h)
```

`algorithms.py` also contains:

```python
depth_limited_search(problem, limit=50)
bidirectional_search(problem)
```

`depth_limited_search` can be used internally by iterative deepening.
`bidirectional_search` is not imported by the facade and is optional.

Keep the signatures unchanged unless `Source/engine/solver.py` is updated at the
same time.

## 3. Return contract

Every required algorithm must return:

```python
[goal_node, explored_ordered, elapsed_ms]
```

- `goal_node`: a real `Node` containing the goal state, or `None` if no solution
  was found.
- `explored_ordered`: a list of expanded nodes or states, in expansion order.
  The UI uses `len(explored_ordered)` as the expanded-node metric. The solution
  playback view accepts either `Node` objects or `State` objects.
- `elapsed_ms`: search time in milliseconds as a numeric value.

The goal node must be a `Node`, not a bare `State`, because the UI calls:

```python
goal_node.path()
goal_node.path_cost
```

through `SolveResult` in `Source/engine/solver.py`.

`Source/engine/solver.py` wraps the tuple in `SolveResult`:

```python
SolveResult(
    algorithm=algorithm,
    level_number=problem.level.level,
    goal_node=goal_node,
    explored=explored_ordered,
    elapsed_ms=elapsed_ms,
)
```

## 4. Problem interface

Algorithms should use only these methods and attributes.

| API | Meaning |
| --- | --- |
| `problem.initial` | Starting `State` |
| `problem.goal_test(state)` | True only for a standing full block on the goal |
| `problem.actions(state)` | Legal action strings: `UP`, `DOWN`, `LEFT`, `RIGHT`, and possibly `SWITCH` |
| `problem.result(state, action)` | Next `State` for a legal action |
| `problem.path_cost(g, state, action, next_state)` | Step cost; currently `g + 1` |
| `problem.h1(node)` | A* heuristic; returns Manhattan distance divided by two for whole blocks and `0` for split states |

Use `Node.expand(problem)` to generate children. It calls `actions`, `result`,
and `path_cost` in the correct order:

```python
for child in node.expand(problem):
    ...
```

`State` equality and hashing include:

```text
position, bridge configuration, split status, active cube
```

Two states that differ only in bridge configuration or active split cube are
different states and must both be kept in the visited structure.

## 5. Generic graph-search template

All required algorithms follow the same search-problem skeleton:

```python
from collections import deque

root = Node(problem.initial)
frontier = ...
explored = []
visited = set()

if problem.goal_test(root.state):
    return [root, explored, elapsed_ms]

while frontier:
    node = frontier.pop()          # queue, stack, or priority queue
    if node.state in visited:
        continue
    visited.add(node.state)
    explored.append(node)

    if problem.goal_test(node.state):
        return [node, explored, elapsed_ms]

    for child in node.expand(problem):
        if child.state not in visited:
            frontier.append(child)

return [None, explored, elapsed_ms]
```

The differences between algorithms are the frontier type, priority function,
and duplicate-handling policy.

## 6. Algorithm-specific requirements

### BFS

- Frontier: FIFO queue.
- Use `collections.deque`.
- Add each state to `visited` when it is enqueued to avoid duplicates.
- With the default cost `1` per action, BFS returns a shortest solution.
- Goal test may be done on expansion or generation. If testing on generation,
  still return the actual goal `Node`.

### DFS

- Frontier: LIFO stack, usually a Python list.
- Use a visited set to avoid cycles.
- DFS is complete for the finite state graph but does not guarantee a shortest
  solution.
- Return the goal node when found.

### Iterative Deepening Search

- Implement a depth-limited DFS helper, either using
  `depth_limited_search(problem, limit)` or an internal recursive helper.
- Avoid cycles on the current path.
- Repeat with increasing depth limits until a solution is found.
- Distinguish three outcomes: goal node, cutoff, and failure.
- Do not use a hardcoded shallow limit that cannot reach advanced-level
  solutions. A reasonable upper bound can be derived from the state space or
  stopped when the depth-limited search returns failure rather than cutoff.
- Report the total explored list across all iterations.

### Uniform Cost Search

- Frontier: priority queue ordered by `g(n) = node.path_cost`.
- Do not use a FIFO queue.
- Fix the cost function before implementing UCS.
- Goal test on **pop**, not on generation, so the first popped goal is optimal.
- Use `best_g[state]` to keep the cheapest known cost for each state.
- With lazy deletion, skip stale entries:
  ```python
  g, _, node = heapq.heappop(frontier)
  if g != best_g.get(node.state):
      continue
  ```
- If all actions cost `1`, UCS behaves like BFS and the assignment's intended
  non-uniform-cost requirement is not demonstrated. Update
  `Bloxorz.path_cost` with a documented cost model if a non-uniform cost is
  required by the report.

### A*

- Frontier: priority queue ordered by `f(n) = g(n) + h(n)`.
- Use `problem.h1(node)` as the heuristic supplied by the facade.
- Goal test on **pop**.
- Use `best_g[state]` with lazy deletion, as in UCS.
- The heuristic must be admissible with respect to the chosen cost function.
- `h1` uses Manhattan distance divided by two. It is admissible when every
  action costs at least `1`; `h1` returns `0` for split states, which is weak but
  admissible.
- If the cost function is changed, re-check admissibility. In particular,
  Manhattan distance divided by two may overestimate if the minimum action cost
  is greater than `1`, or if switch/teleport moves have unusual costs.

### Bidirectional search

Optional and not connected to the UI facade. It can be left as a placeholder or
implemented separately. If implemented, remember that bridge configuration and
split state participate in reverse-search conditions, and that reverse
successors are not automatically provided by `problem.result`.

## 7. Priority queue and duplicate detection pattern

Use `heapq` with a counter tiebreaker so nodes with equal priority do not need
to be compared by `Node`:

```python
import heapq
import itertools

counter = itertools.count()
frontier = []
heapq.heappush(frontier, (priority, next(counter), node))
priority, _, node = heapq.heappop(frontier)
```

Recommended structures:

- `visited`: `set` of `State`.
- `best_g`: `dict[State, number]` for UCS and A*.
- `explored_ordered`: list of expanded `Node` objects.

Do not mutate a `State` after putting it in a set or dictionary. State fields are
effectively immutable for search purposes.

## 8. Metrics

The project requires these measurements for each algorithm.

### Search time

Use a monotonic timer:

```python
from time import perf_counter

start = perf_counter()
# search
elapsed_ms = (perf_counter() - start) * 1000.0
```

### Expanded nodes

Record each node when it is expanded, not every generated child. The UI counts
`len(explored_ordered)`.

### Solution length

The UI derives solution length from the goal node:

```python
len(goal_node.solution())   # number of actions
```

`goal_node.path_cost` is the solution cost, which equals the move count when
every action costs `1`.

### Peak memory

The current `SolveResult` does not store peak memory. If the report requires it,
extend the solver contract consistently:

```python
import tracemalloc

tracemalloc.start()
# search
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
peak_bytes = peak
```

Then:

1. Return a fourth value from every algorithm, e.g.
   `[goal_node, explored_ordered, elapsed_ms, peak_bytes]`.
2. Add `peak_memory` to `SolveResult`.
3. Update `solve_problem` to unpack and store it.
4. Display it in `Source/ui/algorithm_views.py`.

Measure memory after loading the problem and before starting the search if the
goal is comparing algorithm frontier/search memory rather than level-loading
memory.

## 9. Heuristic notes

- `problem.h1(node)` expects a `Node`, not a `State`.
- For whole blocks it uses the closest occupied cell and Manhattan distance
  divided by two.
- For split states it returns `0`.
- With uniform unit costs, Manhattan distance divided by two is admissible.
- A* should use `f = g + h`, not `h` alone. Best-first search without `g` is not
  exposed by the current UI.
- If more heuristics are added, update `Source/engine/solver.py` and the
  algorithm selector deliberately rather than silently changing the meaning of
  the existing `A*` entry.

## 10. Testing and integration

After implementing the algorithms, these existing checks should pass:

```bash
cd Source
python3 -m unittest tests.test_logic.LevelTests -v
python3 -m unittest tests.test_logic.SearchTests -v
python3 -m unittest tests.test_logic.SessionTests -v
python3 -m unittest discover -s tests -p 'test_advanced.py' -v
```

Relevant expectations:

- All levels load successfully.
- Every algorithm in `ALGORITHM_NAMES` solves level 1.
- A returned solution path reaches the goal when replayed through
  `GameSession.move`.
- `GameSession.request_hint()` works; it uses Uniform Cost Search.
- Advanced levels use bridge, split, and active-cube state correctly.
- Solution playback in the UI works, which requires a real goal `Node` with a
  complete parent chain.

Manual UI checks:

1. Open `Algorithms`.
2. Select each algorithm and a level.
3. Confirm solution cost, expanded nodes, and time appear.
4. Press `S` to replay the solution.
5. Press `N` to view explored nodes.
6. Confirm the displayed path reaches the goal.

## 11. Implementation checklist

- [ ] BFS implemented and returns a shortest path for unit costs.
- [ ] DFS implemented with cycle protection.
- [ ] IDS implemented with increasing depth limits and cutoff handling.
- [ ] UCS implemented with a priority frontier and goal test on pop.
- [ ] A* implemented with `f = g + h1` and goal test on pop.
- [ ] Every function returns `[goal_node, explored_ordered, elapsed_ms]`.
- [ ] `goal_node` is a `Node` with a complete `parent` chain.
- [ ] `explored_ordered` records expanded nodes in order.
- [ ] Search time is measured in milliseconds.
- [ ] Visited/best-cost structures include bridge state, split state, and active
      cube through `State` equality and hashing.
- [ ] `SWITCH` actions are handled exactly like other actions from
      `problem.actions`.
- [ ] The initial-state goal case returns a valid root node.
- [ ] Level 1 passes all solver tests.
- [ ] Solution replay reaches the goal in the UI.
