# Bloxorz Problem Interface and State Representation

This document describes the data structures and functions that search
algorithms must use. The search implementations in
`Source/engine/algo_implementation/algorithms.py` are placeholders; the problem, level, state,
node, session, solver facade, and UI remain implemented.

## 1. Coordinates and tiles

- `x` is the column index and `y` is the row index.
- The board is stored as `level.map[y][x]`.
- `level.size` is both the width and height of the square board.
- A tile is walkable only when it is inside the board and `level.map[y][x] == 1`.
- `0` means void.
- The goal is a normal walkable cell at `level.end`; the UI draws it in red.

`Level.is_tile_available(x, y)` is the single source of truth for legality:

```python
def is_tile_available(self, x, y):
    return (0 <= x < self.size and 0 <= y < self.size
            and self.map[y][x] == 1)
```

## 2. State representation

`State` is defined in `Source/engine/problem.py`:

```python
class State:
    def __init__(self, position):
        self.position = position
```

`position` is a list whose length determines the block orientation.

### Standing

```text
position = [x, y]
```

The block occupies exactly one cell.

### Lying horizontally

```text
position = [x1, y1, x2, y2]
x1 != x2, y1 == y2, x2 == x1 + 1
```

The block occupies `(x1, y1)` and `(x2, y2)`. The first endpoint has the
smaller `x`.

### Lying vertically

```text
position = [x1, y1, x2, y2]
x1 == x2, y1 != y2, y1 == y2 + 1
```

The block occupies `(x1, y1)` and `(x2, y2)`. The first endpoint has the
larger `y`.

The vertical ordering is intentional. Do not reorder the endpoints. The
transition rules assume the order produced by `Bloxorz.result`.

### Equality and hashing

```python
def __hash__(self):
    return hash(str(self.position))

def __eq__(self, other):
    return isinstance(other, State) and self.position == other.position
```

Two states are equal exactly when their `position` lists are equal. Because the
position is a list, do not mutate a state that has already been placed in a
visited set or frontier.

## 3. Level representation

`Level` is defined in `Source/engine/level.py`. A level JSON file has this form:

```json
{
  "level": 1,
  "size": 10,
  "start": [4, 2],
  "end": [4, 8],
  "map": [[0, 0, 0], ...]
}
```

After loading:

- `level.map` is the 2D tile grid.
- `level.level` is the level number.
- `level.size` is the board dimension.
- `level.start` is the starting coordinate as `[x, y]`.
- `level.end` is the goal coordinate as `[x, y]`.

The loader reverses the JSON `start` and `end` pairs before storing them. For
example, JSON `[4, 2]` becomes `[2, 4]`, interpreted as `x = 2, y = 4`.

## 4. Problem object

`Bloxorz` is defined in `Source/engine/problem.py` and extends the abstract
`Problem` from `Source/engine/algo_implementation/problem.py`.

```python
problem = Bloxorz(level_number)
```

Relevant attributes:

- `problem.level`: the loaded `Level`.
- `problem.initial`: a `State` built from `level.start`.
- `problem.goal`: a `State` built from `level.end`, always standing.

## 5. Required problem functions

Search implementations must call only these functions. They must not reach into
the level grid directly unless they are implementing the problem interface
itself.

### `problem.actions(state) -> list[str]`

Returns the legal action strings for the state. Possible actions are:

```text
UP, DOWN, LEFT, RIGHT
```

An action is absent when the move would leave the board or touch a void cell.

Direction semantics in board coordinates:

- `UP` increases `y`.
- `DOWN` decreases `y`.
- `LEFT` decreases `x`.
- `RIGHT` increases `x`.

### `problem.result(state, action) -> State`

Returns the state reached by applying a legal action. Do not call it with an
illegal action.

### `problem.goal_test(state) -> bool`

Inherited from `Problem`. It compares the state to `problem.goal`, so the stage
is won only when the block is standing at `[x, y]` equal to `level.end`. A lying
block that covers the goal is not a win.

### `problem.path_cost(cost_so_far, state1, action, state2) -> number`

Inherited from `Problem`. The current implementation adds `1` for every action:

```python
return cost_so_far + 1
```

UCS and A* call this through `Node.child_node`.

### `problem.h1(node)`

Heuristic function used by A*. It receives a `Node` and returns a numeric
estimate of the remaining cost. The search algorithm should pass the node, not
`node.state`.

## 6. Transition table

The following transitions are the ones implemented by `Bloxorz.result`. They
assume the canonical representation from Section 2.

### Standing `[x, y]`

| Action | New position | New orientation |
| --- | --- | --- |
| `UP` | `[x, y+2, x, y+1]` | vertical |
| `DOWN` | `[x, y-1, x, y-2]` | vertical |
| `LEFT` | `[x-2, y, x-1, y]` | horizontal |
| `RIGHT` | `[x+1, y, x+2, y]` | horizontal |

### Lying horizontally `[x1, y1, x2, y2]` with `y1 == y2`, `x2 == x1 + 1`

| Action | New position | New orientation |
| --- | --- | --- |
| `UP` | `[x1, y1+1, x2, y2+1]` | horizontal |
| `DOWN` | `[x1, y1-1, x2, y2-1]` | horizontal |
| `LEFT` | `[x1-1, y1]` | standing |
| `RIGHT` | `[x2+1, y2]` | standing |

### Lying vertically `[x1, y1, x2, y2]` with `x1 == x2`, `y1 == y2 + 1`

| Action | New position | New orientation |
| --- | --- | --- |
| `UP` | `[x1, y1+1]` | standing |
| `DOWN` | `[x2, y2-1]` | standing |
| `LEFT` | `[x1-1, y1, x2-1, y2]` | vertical |
| `RIGHT` | `[x1+1, y1, x2+1, y2]` | vertical |

### Legality checks

`Bloxorz.actions` checks every destination cell with
`level.is_tile_available` before returning an action:

- From standing, a roll requires the two cells in the rolling direction.
- Lying along the roll direction, a roll requires the single cell beyond the
  leading endpoint.
- Lying across the roll direction, a roll requires the two adjacent cells
  beside both endpoints.

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
iterative_deepening_search(problem)
uniform_cost_search(problem)
astar_search(problem, h)
```

Each function must return a three-element sequence:

```python
[goal_node, explored_ordered, elapsed_ms]
```

- `goal_node`: the goal `Node`, or `None` when no solution exists.
- `explored_ordered`: the expanded/visited items in order. The UI accepts
  either `Node` objects or `State` objects and uses `len()` as the expanded-node
  metric.
- `elapsed_ms`: search time in milliseconds as a number.

`SolveResult.solution_path()` returns `goal_node.path()`, and
`SolveResult.solution_cost` returns `goal_node.path_cost`. The UI reads both.
Therefore `goal_node` must be a real `Node` when a solution is found.

Algorithm names exposed to the UI:

```text
DFS
BFS
Iterative DFS
Uniform Cost Search
A*
```

`A*` maps to `astar_search` with `problem.h1` as the heuristic.

## 9. Implementation notes

- Return the goal node as soon as the goal is removed from the frontier, or
  when it is generated, but ensure the returned path is complete.
- Always keep a visited set or equivalent duplicate detection. The graph is
  finite but cycles are possible.
- Do not modify `State.position` in place.
- Do not build states by guessing the endpoint order; use `problem.result`.
- If the initial state is already the goal, return a valid root `Node`.
- The current board has no advanced tiles. Fragile tiles, bridges, switches,
  splitting, and bridge configuration are not represented in `State` or
  `Level`. Adding them requires changing `State`, its equality/hash, the level
  loader, and `Bloxorz.actions`/`result` first.
- The current cost function is uniform (`+1` per action). A non-uniform UCS cost
  must be implemented in `Bloxorz.path_cost`, and A* heuristics must remain
  admissible for that cost.
