# Bloxorz Solver Implementation Guide

This document is for the member implementing the search algorithms. The
supported BFS, DFS, UCS and A* functions are implemented in
`Source/engine/algo_implementation/algorithms.py`. Independent DLS/bidirectional
functions remain explicit stubs; IDS has been removed. The problem, level, state, node, solver facade,
session and UI are implemented and should not be duplicated.

Read also:

- [`ALGORITHM_IMPLEMENTATION_GUIDE.md`](ALGORITHM_IMPLEMENTATION_GUIDE.md) for
  the state, level, and problem interface.
- [`ADVANCED_MECHANICS.md`](ADVANCED_MECHANICS.md) for fragile tiles, bridges,
  switches, and split-cube rules.

## 1. Files and responsibilities

| File | Responsibility |
| --- | --- |
| `Source/engine/algo_implementation/algorithms.py` | Supported BFS/DFS/UCS/A* implementations and legacy stubs |
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
uniform_cost_search(problem)
astar_search(problem, h)
```

`algorithms.py` also contains:

```python
depth_limited_search(problem, limit=50)
bidirectional_search(problem)
```

`depth_limited_search` and `bidirectional_search` are independent, optional
stubs, not imported by the facade. Removed IDS names are unknown algorithms.

Keep the signatures unchanged unless `Source/engine/solver.py` is updated at the
same time.

## 3. Return contract

Each of the four supported algorithms returns (legacy stubs raise
`NotImplementedError` instead):

```python
[goal_node, explored_ordered, elapsed_ms]
```

- `goal_node`: a real `Node` containing the goal state, or `None` if no solution
  was found.
- `explored_ordered`: valid frontier pops in order, including the goal.
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
| `problem.path_cost(g, state, action, next_state)` | Cumulative cost: `g + 1`, or `g + 3` for a fragile landing (see below) |
| `problem.h1(node)` | Unified relaxed point distance: `ceil(min(d(cell)) / 2)`, for all orientations and split states |

Use `Node.expand(problem)` to generate children. It calls `actions`, `result`,
and `path_cost` in the correct order:

```python
for child in node.expand(problem):
    ...
```

### Bloxorz cost model

`Bloxorz.path_cost` overrides the generic `Problem.path_cost`, which still
adds 1 for other problems. Every legal Bloxorz action costs 1, plus a penalty
of 2 if the moved part lands on at least one fragile tile. Charge the penalty
only once per action, even for two fragile tiles; charge again on each
subsequent fragile landing. Leaving fragile for ordinary floor costs 1.
This is an avoidance score, not a falling probability or a change to support rules.

- `SWITCH` always costs 1, including when either cube is on fragile.
- While split, inspect only the moving cube's destination. A stationary cube
  on fragile adds no penalty, including on the move that merges the cubes;
  coordinate sorting after a merge does not change which cube moved.
- A whole block activating split/teleport moves both cubes: inspect both final
  destinations, including when adjacent targets merge immediately.
- Bridges, switches and split tiles have no extra penalty. Invalid actions
  are still rejected by the existing engine before costs are accumulated.

Thus `C = number_of_actions + 2 * number_of_surcharged_actions`, including
`SWITCH` in the action count. BFS minimizes rolling MOVES; UCS minimizes `C`.
For example, 6 actions with 3 surcharges cost 12, while 10 ordinary actions
cost 10. `Node.depth` / `SolveResult.action_count` count all actions, including
`SWITCH`. `SolveResult.solution_length` and the displayed MOVES count only
non-`SWITCH` actions (rolls in Bloxorz). Other action labels in generic graph
problems still count; counting is not restricted to the four direction names.
`Node.path_cost` / `SolveResult.solution_cost` are total cost and may differ.
For example, `RIGHT -> SWITCH -> UP` without fragile landings is 3 actions,
2 MOVES and COST 3. Replay progress indexes all 3 primitive actions. The win
screen's "best possible N moves" comes from BFS's minimum rolling count,
not from a DFS/UCS/A* result or from a claim of minimum cost.
The relaxed heuristic and its lower-bound argument are described in section 9.

`State` equality and hashing include:

```text
position, bridge configuration, split status, active cube
```

Two states that differ only in bridge configuration or active split cube are
different states and must both be kept in the visited structure.

### Shared rolling search model

`engine/search_model.py` supplies `rolling_search`, applied at the four public
implemented entry points in `algo_implementation/algorithms.py`. Both direct
algorithm calls and `solve` / `solve_problem` use it for Bloxorz. Generic
Problems retain their own actions and edges; manual Bloxorz play is unchanged.

Internally one edge is a roll of the whole block, or a roll of either split
cube. The edge is `(direction,)` for the active cube or `('SWITCH', direction)`
for the other cube; there is no standalone SWITCH edge. Costs call the existing
`Bloxorz.path_cost` once per primitive transition in order, using the actual
intermediate state. A select-and-roll edge costs 2 normally, or 4 if the roll
has a fragile penalty. No input state or board is mutated.

Before returning, a cache expands internal Node chains into ordinary primitive
Node chains, including intermediate SWITCH states. Public `solution()` still
returns strings; `parent`, `action`, `path_cost` and `depth` describe these
primitive edges consistently. A given internal Node is converted once. Only
recorded search endpoints appear in explored; conversion adds no intermediate
SWITCH entries. All four searches record the goal on its valid pop and stop
without generating its children. Reported time includes the adapter, any
heuristic table construction, search and result conversion. A* priority logic
remains `g + h` with best-g tracking and stale-entry rejection.

## 5. Generic graph-search template

All required algorithms follow the same search-problem skeleton:

```python
from collections import deque

root = Node(problem.initial)
frontier = ...
explored = []
visited = set()

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
- BFS returns a shortest solution in rolling MOVES for Bloxorz (edges for a
  generic Problem), not necessarily the cheapest
  solution under the fragile-penalty model.
- Record the valid popped node, then goal-test it and return immediately on
  success. Do not stop when a goal is merely generated or expand its children.

### DFS

- Frontier: LIFO stack, usually a Python list.
- Use a visited set to avoid cycles.
- DFS is complete for the finite state graph but does not guarantee a shortest
  solution.
- Return the goal node when found.

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
- Use the Bloxorz cost model above through `Node.expand`; do not hardcode
  unit costs in UCS. Compare total cost with BFS separately from action count.

### A*

- Frontier: priority queue ordered by `f(n) = g(n) + h(n)`.
- Use `problem.h1(node)` as the heuristic supplied by the facade.
- Goal test on **pop**.
- Use `best_g[state]` with lazy deletion, as in UCS.
- The heuristic must be admissible with respect to the chosen cost function.
- `h1` uses the same relaxed-distance formula for every level and state;
  see section 9 for the graph definition and consistency argument.

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

Record each valid frontier pop, including the goal, before returning. UCS/A*
discard stale entries first. Do not generate the goal's children or drain the
frontier; an initial goal gives exactly one entry. A* reopening a state at a
better g records that valid pop again, so the list is not forcibly deduplicated.
Intermediate SWITCH Nodes inserted for public replay are not added. The UI
keeps the label Expanded and counts `len(explored_ordered)`; Show explored ends
at the goal on success. This metric counts considered nodes, including a goal
whose children are not expanded.

### Solution length

The facade reports two lengths from the public primitive Node path:

```python
result.action_count       # len(goal_node.solution()), includes SWITCH
result.solution_length    # non-SWITCH actions; MOVES shown in the UI
```

`goal_node.path_cost` is the solution cost. With unit costs it equals the
action count, which can exceed MOVES when switching cubes. The fragile model
adds 2 per surcharged action using the full action count, never MOVES.
`GameSession.action_count`, `.moves` and `.cost` track actual accepted play;
reset clears all three. Search, hints and state display do not spend play cost
or actions. In-game Solve starts from the current state; Lab starts from the stage start.

### Peak memory

`solve_problem(..., measure_memory=True)` runs the same search a second time
under `tracemalloc`; `SolveResult.peak_memory_kb` is the traced peak above the
starting allocation baseline, divided by 1024. Elapsed time comes only from
the first, untraced run. It is traced Python allocation, not whole-process RSS.

`rolling_search` clears the problem's heuristic cache inside each timed/traced
run. Both measurements include topology-key construction, reverse graph and
distance-table construction when h1 is used, search structures and conversion
to primitive Node paths. A warm table from Hint or the time run cannot hide
its build from the memory run. Level/JSON loading, GUI, playback and process
startup are outside both measurements. The public algorithm return format
stays three elements; memory is stored by the facade, not returned by algorithms.

## 9. Heuristic notes

`problem.h1(node)` keeps the existing Node interface. The assignment's suggestion
to relax the problem is distinct from this repository's concrete design below:
potential floor cells, directed zero-length teleports, and point distance scaled
to rolls are the team's chosen implementation.

**One graph for every level.** `engine/heuristic.py` includes every potential
floor cell, including fragile and all bridges treated as open, and excludes
void. Orthogonal neighbors have directed edges both ways of length 1. A split
trigger has a directed edge of length 0 to each teleport target. Walking past
a trigger is allowed without activation. Posture, active cube and support
restrictions are relaxed. Levels without teleports simply lack those zero edges.

0-1 BFS on the reversed graph computes d(cell), the distance TO the goal.
Teleport trigger -> target is reversed as target -> trigger, not the other
way. For all occupied cells, `D = min(d(cell))`, `h = ceil(D / 2)`; finite integer
D uses `(D + 1) // 2`. Split states use this formula too; there is no separate
Manhattan branch, blanket split-zero rule, or multiplier for fragile penalties.

**Why this matches the real engine.** Each destination cell of a legal roll
has some source cell that reaches it within two point steps: tipping a standing
block uses one or two adjacent cells; standing a lying block uses its front
cell plus one; sideways rolls and cube moves use one. The stationary split
cube maps to itself. SWITCH changes no occupied cells. A merge changes only
representation. Teleport activation is reached by a roll and then a zero edge
to either target, including adjacent targets that merge immediately. All
intermediate cells are potential floor; bridge and fragile restrictions only
remove real actions, so they do not invalidate these relaxed paths.

Choose the destination attaining D(s'). Its source gives
`D(s) <= 2 + D(s')`, hence `h(s) <= 1 + h(s') <= edge_cost + h(s')`, since every
rolling edge costs at least 1, including the optional SWITCH fee. A standalone
manual SWITCH leaves h unchanged and costs 1. `h(goal) = 0`, so consistency
telescopes along every solution to prove admissibility for the current rules.

Unreachable point distances stay infinity. A state with D=infinity cannot have
a real transition to finite D by the same mapping, and cannot reach the goal;
the consistency argument holds in the extended nonnegative reals. Replacing
infinity with zero would lose this argument and is deliberately avoided.

**Cache and evidence.** The per-problem cache key snapshots potential cells,
teleport links and goal coordinates, never temporary Hint initial or bridge
flags. Changed topology/goal invalidates it. Each public search clears it for
fair measurement; within a run, states reuse the table. There is no global
cache shared between levels.

`test_relaxed_heuristic.py` checks every reachable state and edge on small real
Level/GameSession fixtures against independent all-pairs Floyd-Warshall point
distances and reverse-Dijkstra optimal remaining game costs. A custom teleport
shortcut needs cost 3 although the old initial Manhattan estimate was 4; new
h is 2. This counterexample is a temporary fixture, not a catalog JSON level.

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

- Supported UI solvers are BFS, DFS, Uniform Cost Search, A*, in that order.
  The team chose DFS for DFS-or-IDS and removed IDS. Only independent
  DLS/bidirectional stubs remain; they are not selectable or part of Run all.
- All levels load successfully.
- Every algorithm in `ALGORITHM_NAMES` solves level 1.
- A returned solution path reaches the goal when replayed through
  `GameSession.move`.
- `GameSession.request_hint()` works; it uses Uniform Cost Search.
- Advanced levels use bridge, split, and active-cube state correctly.
- Solution playback in the UI works, which requires a real goal `Node` with a
  complete parent chain.

The four core regression modules are `test_bfs.py`, `test_ucs.py`,
`test_path_cost.py` and `test_relaxed_heuristic.py`. `test_bloxorz_integration.py`
groups rolling-edge semantics, full primitive replay with SWITCH and metrics,
session cost/reset, explored/goal/reopening contracts, and bridge/switch rules.
Legal bridge/split helpers are local to that integration module. The independent
heuristic oracles remain in the core suite. GUI harnesses added during development
have been removed; this suite does not replace manual GUI verification.

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
- [ ] Independent DLS/bidirectional calls explicitly raise `NotImplementedError`
      (IDS implementation, aliases and dispatch have been removed).
- [ ] UCS implemented with a priority frontier and goal test on pop.
- [ ] A* implemented with `f = g + h1` and goal test on pop.
- [ ] Every supported function returns `[goal_node, explored_ordered, elapsed_ms]`.
- [ ] `goal_node` is a `Node` with a complete `parent` chain.
- [ ] `explored_ordered` records valid pops in order, including the goal once.
- [ ] Search time is measured in milliseconds.
- [ ] Visited/best-cost structures include bridge state, split state, and active
      cube through `State` equality and hashing.
- [ ] `SWITCH` actions are handled exactly like other actions from
      `problem.actions`.
- [ ] The initial-state goal case returns a valid root node.
- [ ] Level 1 passes all solver tests.
- [ ] Solution replay reaches the goal in the UI.
