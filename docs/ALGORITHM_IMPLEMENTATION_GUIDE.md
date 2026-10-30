# Bloxorz Problem Interface and State Representation

This document describes the data structures and functions that search
algorithms must use. The search implementations in
`Source/engine/algo_implementation/algorithms.py` include implemented BFS, DFS,
UCS and A*. Independent DLS/bidirectional stubs remain outside the supported UI
choices; IDS has been removed. The problem, level, state, node, session, solver facade and UI are implemented.

See [`SOLVER_IMPLEMENTATION.md`](SOLVER_IMPLEMENTATION.md) for algorithm-specific
requirements, pseudocode, metrics, and the testing checklist.

## 1. Coordinates and tiles

- `x` is the column index and `y` is the row index.
- `level.size` is both the width and height of the square board.
- `level.kinds[(x, y)]` is the tile character at a cell.
- Missing cells are void.
- The goal is the cell at `level.end`; only a standing full block there wins.

Advanced tile characters:

| Character | Tile |
| --- | --- |
| `b` | floor |
| `e` | goal |
| `f` | fragile |
| `s` | soft switch |
| `h` | heavy switch |
| `v` | split switch |
| `l`, `r` | bridge, initially closed |
| `k`, `q` | bridge, initially open |

A tile's final support depends on the block shape and the current bridge
configuration. Use `problem.actions(state)` and `problem.result(state, action)`
rather than inspecting the grid directly.

The engine evaluates support through `Bloxorz._floor(cell, bridges)`: static
tiles are solid, a fragile tile is solid except under a standing full block,
and a bridge is solid only while open.

See [`ADVANCED_MECHANICS.md`](ADVANCED_MECHANICS.md) for the complete tile,
switch, bridge, and split rules.

## 2. State representation

`State` is defined in `Source/engine/problem.py`:

```python
class State:
    def __init__(self, position, bridges=(), split=False, active=0):
        self.position = position
        self.bridges = tuple(bridges)
        self.split = split
        self.active = active
```

- `position` stores cell coordinates as `[x, y]` pairs.
- `bridges` stores the open (`1`) or closed (`0`) state of every bridge.
- `split` is true when the block is two independent `1 x 1 x 1` cubes.
- `active` is `0` or `1` and selects which split cube moves.

### Whole block

**Standing:**

```text
position = [x, y]
```

**Lying horizontally:**

```text
position = [x1, y1, x2, y2]
y1 == y2, x2 == x1 + 1
```

**Lying vertically:**

```text
position = [x1, y1, x2, y2]
x1 == x2, y2 == y1 + 1
```

The engine stores whole-block cells in sorted order after a move. Do not rely
on endpoint ordering when constructing states manually; use
`problem.result(state, action)`.

### Split block

```text
position = [x0, y0, x1, y1]
```

The first pair is cube `0` and the second pair is cube `1`. `active` selects
which cube the next directional move applies to. When the cubes merge, the
result is a whole lying block stored in sorted order.

### Equality and hashing

```python
def _key(self):
    return (tuple(self.position), self.bridges, self.split, self.active)

def __hash__(self):
    return hash(self._key())

def __eq__(self, other):
    return isinstance(other, State) and self._key() == other._key()
```

Two states are equal only when the block configuration, bridge configuration,
split status, and active cube are all equal. Do not mutate state fields after a
state has been placed in a visited set or frontier.

## 3. Level representation

`Level` is defined in `Source/engine/level.py`. Advanced levels use a `tiles`
grid plus optional `switches` and `splits`:

```json
{
  "level": 22,
  "size": 10,
  "start": [4, 2],
  "end": [4, 8],
  "tiles": ["bbbsbb...", "..."],
  "switches": [
    {"at": [2, 2], "bridges": [[4, 4, "onoff"], [5, 4, "off"]]}
  ],
  "splits": [
    {"at": [13, 1], "cubes": [12, 1, 2, 1]}
  ]
}
```

Legacy levels may use a `map` grid of `0`/`1` values instead of `tiles`.

After loading:

- `level.kinds` maps `(x, y)` to the tile character.
- `level.level` is the level number.
- `level.size` is the board dimension.
- `level.start` and `level.end` are `[x, y]` coordinates.
- `level.bridge_index` maps bridge cells to indices in the bridge-state tuple.
- `level.bridges_open` is the initial bridge-state tuple.
- `level.switches` maps a switch cell to `(bridge_x, bridge_y, mode)` links.
- `level.splits` maps a split-switch cell to two cube coordinates.

The loader reverses the JSON `start` and `end` pairs before storing them. For
example, JSON `[4, 2]` becomes `[2, 4]`, interpreted as `x = 2, y = 4`.

Switch `at`, bridge coordinates, split `at`, and split cube coordinates are
stored as `[x, y]` directly.

Supported switch modes are:

- `onoff` — toggle every linked bridge
- `on` — permanently open every linked bridge
- `off` — permanently close every linked bridge

## 4. Problem object

`Bloxorz` is defined in `Source/engine/problem.py` and extends the abstract
`Problem` from `Source/engine/algo_implementation/problem.py`.

```python
problem = Bloxorz(level_number)
```

Relevant attributes:

- `problem.level`: the loaded `Level`.
- `problem.initial`: a `State` built from `level.start` and `level.bridges_open`.
- `problem.goal`: a `State` built from `level.end`, always standing.

## 5. Required problem functions

Search implementations must call only these functions. They must not reach into
the level grid directly unless they are implementing the problem interface
itself.

### `problem.actions(state) -> list[str]`

Returns the legal action strings for the state. Possible actions are:

```text
UP, DOWN, LEFT, RIGHT
SWITCH
```

`SWITCH` is present only while the block is split and changes which cube is
controlled without moving either cube.

A directional action is absent when it would leave the board, enter a void or
closed bridge, or break a fragile tile under a newly standing full block.

Direction semantics in board coordinates:

- `UP` increases `y`.
- `DOWN` decreases `y`.
- `LEFT` decreases `x`.
- `RIGHT` increases `x`.

### `problem.result(state, action) -> State`

Returns the state reached by applying a legal action. `SWITCH` is valid only
when `state.split` is true. Do not call it with an illegal action.

### `problem.goal_test(state) -> bool`

Implemented by `Bloxorz`. The stage is won only when the block is not split
and is standing at `[x, y]` equal to `level.end`. A lying block that covers the
goal is not a win, and a split cube resting on the goal is not a win.

### `problem.path_cost(cost_so_far, state1, action, state2) -> number`

Bloxorz overrides the generic `Problem` default (`+1`) with a fragile penalty:

```python
return cost_so_far + 1 + (2 if moved_part_lands_on_fragile else 0)
```

`SWITCH` always costs 1. A split move inspects only the moving cube's destination,
including a merge; activating split/teleport inspects both destination cells.
The penalty is charged once per action, regardless of the number of fragile
cells. See [the complete cost model](SOLVER_IMPLEMENTATION.md#bloxorz-cost-model).
UCS and A* call this through `Node.child_node`; action count and total cost are separate.

### `problem.h1(node)`

Heuristic function used by A*. It receives a `Node` and returns a numeric
estimate of the remaining cost: `ceil(min(d(occupied_cell)) / 2)` for standing,
lying and split states on every level. d is the point distance to the goal
with bridges open, fragile support allowed and directed zero-cost teleport
links; it is computed by reverse 0-1 BFS. Infinite distances remain infinite.
The search algorithm passes the Node, not `node.state`. See
`SOLVER_IMPLEMENTATION.md#9-heuristic-notes` for the consistency argument,
cache and exact scope of time/memory measurement.

## 6. Transition table

The following transitions are the ones implemented by `Bloxorz.result`. The
engine stores whole-block endpoint cells in sorted order.

### Standing `[x, y]`

| Action | New position | New orientation |
| --- | --- | --- |
| `UP` | `[x, y+1, x, y+2]` | vertical |
| `DOWN` | `[x, y-2, x, y-1]` | vertical |
| `LEFT` | `[x-2, y, x-1, y]` | horizontal |
| `RIGHT` | `[x+1, y, x+2, y]` | horizontal |

### Lying horizontally `[x1, y1, x2, y2]` with `y1 == y2`, `x1 < x2`

| Action | New position | New orientation |
| --- | --- | --- |
| `UP` | `[x1, y1+1, x2, y2+1]` | horizontal |
| `DOWN` | `[x1, y1-1, x2, y2-1]` | horizontal |
| `LEFT` | `[x1-1, y1]` | standing |
| `RIGHT` | `[x2+1, y2]` | standing |

### Lying vertically `[x1, y1, x2, y2]` with `x1 == x2`, `y1 < y2`

| Action | New position | New orientation |
| --- | --- | --- |
| `UP` | `[x1, y2+1]` | standing |
| `DOWN` | `[x1, y1-1]` | standing |
| `LEFT` | `[x1-1, y1, x2-1, y2]` | vertical |
| `RIGHT` | `[x1+1, y1, x2+1, y2]` | vertical |

### Split cubes

A directional action moves only the cube at index `state.active` by one cell.
The other cube stays put. If the cubes become 4-adjacent, they merge into a
lying whole block immediately. `SWITCH` changes `state.active` without moving
either cube.

### Legality checks

Directional actions are generated only when every occupied destination cell is
supported:

- From standing, a roll requires the two cells in the rolling direction.
- Lying along the roll direction, a roll requires the single cell beyond the
  leading endpoint.
- Lying across the roll direction, a roll requires the two adjacent cells
  beside both endpoints.
- A split move requires the active cube's destination and the stationary cube's
  cell to be supported.
- Fragile tiles fail under a newly standing full block.
- Closed bridges behave as void.
- Switch effects are applied before the final support check.
- A split switch teleports the block to its configured cubes. Adjacent target
  cubes merge immediately.

## 7. Node contract

`Node` is defined in `Source/engine/algo_implementation/node.py`. Algorithms may use it as the
search-tree node.

Attributes:

- `state`: the `State`.
- `parent`: the previous `Node`, or `None` for the root.
- `action`: the action that produced this node.
- `path_cost`: cumulative cost `g`.
- `depth`: number of actions from the root.

Methods:

- `expand(problem)` returns child nodes by calling `problem.actions` and
  `problem.result`.
- `child_node(problem, action)` creates one child and calls
  `problem.path_cost`.
- `path()` returns the list of nodes from the root to this node.
- `solution()` returns the list of action strings from the root to this node.

Equality and hashing are based on `state`, so a `set` of visited states can
contain either `State` objects or `Node` objects consistently.

## 8. Search algorithm contract

The facade in `Source/engine/solver.py` imports these functions from
`Source/engine/algo_implementation/algorithms.py`:

```python
depth_first_graph_search(problem)
breadth_first_graph_search(problem)
uniform_cost_search(problem)
astar_search(problem, h)
```

Each function must return a three-element sequence:

```python
[goal_node, explored_ordered, elapsed_ms]
```

- `goal_node`: the goal `Node`, or `None` when no solution exists.
- `explored_ordered`: valid frontier pops in order, including the goal. The UI accepts
  either `Node` objects or `State` objects and uses `len()` as the expanded-node
  metric. Discard stale UCS/A* entries first; record then stop on a goal without
  generating children. An initial goal gives one item. Record valid A* reopens
  again; do not force unique states. Public SWITCH intermediates are not extra pops.
- `elapsed_ms`: search time in milliseconds as a number.

`SolveResult.solution_path()` returns `goal_node.path()`, and
`SolveResult.solution_cost` returns `goal_node.path_cost`. The UI reads both.
Therefore `goal_node` must be a real `Node` when a solution is found.

`SolveResult.action_count` includes every action, including `SWITCH`;
`solution_length` / displayed MOVES exclude `SWITCH`. Generic action labels
other than `SWITCH` count normally. `Node.depth`, parents, paths and action
lists retain every edge. Replay progress uses the complete action list.
COST includes switching: `RIGHT -> SWITCH -> UP` with no fragile landing is
3 actions, 2 MOVES and COST 3. For Bloxorz, BFS is optimal in rolling MOVES.

The four implemented public search functions share the `rolling_search`
adapter in `engine/search_model.py`. Internally an edge is one roll, optionally
preceded by SWITCH to select the other split cube. Its cost sums the existing
primitive `path_cost` calls, including the intermediate state. There is no
standalone SWITCH search edge. Before returning, Node paths are converted once
to primitive actions/states, including SWITCH; public depth still counts
primitive parent edges. Explored retains only recorded search endpoints and
the shared goal-inclusion policy. Direct calls and the solver
facade use the same model; generic Problems and manual Bloxorz actions are unchanged.

Algorithm names exposed to the UI:

```text
BFS
DFS
Uniform Cost Search
A*
```

`A*` maps to `astar_search` with `problem.h1` as the heuristic.
The shared `ALGORITHM_NAMES` list defines the supported UI order and Run all.
DFS is the team's choice for DFS-or-IDS; IDS has no implementation or dispatch.
Independent DLS/bidirectional functions remain explicit `NotImplementedError`
stubs, outside the supported choices.

## 9. Implementation notes

- After stale/duplicate rejection, record a popped node, then goal-test and
  return immediately on success. Do not accept a goal on generation or generate
  its children; keep the returned primitive path complete.
- Always keep a visited set or equivalent duplicate detection. The graph is
  finite but cycles are possible.
- Do not modify `State.position`, `State.bridges`, `State.split`, or
  `State.active` in place.
- Do not build states by guessing the endpoint order; use `problem.result`.
- If the initial state is already the goal, return a valid root `Node`.
- Advanced mechanics are part of the state. Bridge configuration, split status,
  and the active cube all affect `State` equality and hashing.
- `SWITCH` is a zero-movement action available only while split.
- Bridge effects are resolved before support validation. Do not validate a
  destination against the old bridge configuration.
- A split switch may return either a split state or a merged whole lying block
  when its target cubes are adjacent.
- `Bloxorz.path_cost` uses the fragile-penalty model (cost 1 or 3); the generic
  `Problem.path_cost` remains `+1`. A* heuristics must be checked against this
  cost model and split/teleport mechanics.
- See [`ADVANCED_MECHANICS.md`](ADVANCED_MECHANICS.md) for the detailed gameplay
  rules and response checklist.
