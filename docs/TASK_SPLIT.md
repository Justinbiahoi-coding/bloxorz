# Task split – 5 people, Bloxorz Solver product

Scope: the **product** only (game, GUI, solvers, experiments). The report and video are split later.

Principle: each person **owns one module** and touches other people's files as little as possible, to avoid git conflicts. Everyone must still understand the whole project (the instructor may question any member).

## Interface contract (fixed on day 1, do not change on your own)

The engine provides these; solvers and the GUI use only them:

```python
Stage            # loaded from JSON: grid, start, goal, fragile, bridges, switches
State            # immutable, hashable: block position + orientation (or 2 cubes when split),
                 # the cube being controlled, the open/closed state of every bridge
initial_state(stage) -> State
successors(stage, state) -> list[(move, State, cost)]   # legal moves only
is_goal(stage, state) -> bool
```

A solver takes `(stage)` and returns `SolveResult(path, time, peak_memory, expanded, length)`.

## Roles

| # | Role | Main work | Owned files |
|---|---|---|---|
| 1 | **Core engine** (tech lead) | State, orientation transition table, validity/void, win check, JSON loader, unit tests for the transition table. **Fix the interface contract in the first 2 days.** | `bloxorz/state.py`, `bloxorz/stage.py`, `tests/test_core.py` |
| 2 | **Advanced tiles** | Fragile, bridges (toggle/permanent), soft/heavy/split switches, splitting and merging the block, switching the controlled cube. Integrated into `successors`. Works with #1, since both touch the transition function. | `bloxorz/tiles.py`, `tests/test_advanced.py` |
| 3 | **GUI** | pygame: draw the board and every tile kind, the block in its 3 orientations, manual play with the keyboard, New Game / Restart / Solve BFS-DFS-UCS-A* buttons, animate the solution, show win/lose. | `main.py`, `bloxorz/gui.py` |
| 4 | **Basic solvers** | BFS, DFS (or IDS), UCS with a non-uniform cost function. Shared measuring harness for all 4 solvers: time, peak memory (`tracemalloc`), expanded nodes, solution length. | `bloxorz/solvers/base.py`, `bfs.py`, `dfs.py`, `ucs.py` |
| 5 | **A\* + experiments** | A* and its heuristic (admissible under #4's cost function). Design a fixed test set in 4 difficulty groups, the experiment script, tables and charts. | `bloxorz/solvers/astar.py`, `experiments.py`, `stages/*.json` |

## Schedule

| Phase | Milestones |
|---|---|
| Start | #1 finishes the core and the interface contract (day 2). #2 starts fragile tiles and bridges. #3 builds the GUI on a sample stage. #4 writes BFS first, then DFS/UCS. #5 designs the test stages and researches heuristics. |
| Middle | #2 finishes the 3 switch kinds and splitting. #3 wires the Solve buttons and the animation. #4 finishes 3 solvers and the harness. #5 finishes A*. Integration and a full trial run. |
| End | #5 runs the experiments on the fixed test set. Everyone fixes bugs and prepares for the oral check. |

## Working rules
- One branch per person, `feature/<name>`, merged into `main` through a pull request reviewed by at least one other member.
- Any change to the interface contract must be announced to the whole team.
- Everyone can explain their own code and how it fits with the other modules.
