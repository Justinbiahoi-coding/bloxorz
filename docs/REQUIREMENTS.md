# Project 1 – Bloxorz Solver (CSC14003 – Introduction to Artificial Intelligence)

A **group** assignment, about 3 weeks long. Source: `AI - Project 1.pdf`.

## 1. Introduction

Bloxorz is a puzzle game about rolling a 1×1×2 block over a floor of square tiles. The goal is to make the block **drop upright** into the goal hole. Rolling the block off the board loses.

The game suits practising BFS, DFS, UCS and A*: it is fully observable and deterministic, and **the block's orientation is part of the state**, which makes it a good subject for designing admissible heuristics.

## 2. Rules

### 2.1 Layout
A stage is a finite grid of square cells. Each cell is one of:
- **Floor tile**: a normal tile the block can rest on.
- **Empty cell (void)**: no floor; if any part of the block is over a void the block falls, so the move is **illegal**.
- **Goal hole**: the single target cell; the stage is won when the block drops into it.

The block starts **standing** on a given start cell.

### 2.2 Block orientations (3 kinds)
- **Standing**: occupies 1 cell (r, c).
- **Lying horizontally**: occupies (r, c) and (r, c+1).
- **Lying vertically**: occupies (r, c) and (r+1, c).

### 2.3 Moves
Each turn the block rolls in one of 4 directions: **Up, Down, Left, Right**.
- A standing block → lies down over 2 cells in the direction of the roll.
- A block lying **along** the direction of the roll → stands up on 1 cell.
- A block lying **across** the direction of the roll → rolls sideways, stays lying, moves 1 cell.

A move is **illegal** if, after the roll, any cell under the block is void or outside the board (the block must always be fully supported by floor tiles).

### 2.4 Winning
The stage is won when the block drops into the goal hole, which happens only when the block **stands** on the goal cell. A block lying across the goal does **not** win.

### 2.5 Advanced tiles
- **Fragile tile (orange)**: holds the block only while it is **lying**. If the block **stands** on it, the tile breaks and the block falls. The block may lie across a fragile tile.
- **Bridge**: a cell that is open or closed, controlled by switches. A **closed** bridge behaves like a void; an **open** bridge behaves like a normal floor tile. Each switch is linked to one or more bridges.

**3 kinds of switch:**
| Kind | Triggered when |
|---|---|
| Soft (octagon/round) | Any part of the block presses it, standing or lying |
| Heavy (X shape) | Only when the block **stands** on it; lying does not trigger it |
| Split ("( )" shape) | Only when the block **stands** on it; it teleports the block to set positions and **splits it into two 1×1×1 cubes** |

**Effect on bridges** when a switch is triggered:
- **Toggle**: each trigger flips the bridge between open and closed.
- **Permanent**: the bridge is set to a fixed state once triggered.

**Block splitting:**
- The two cubes are controlled **one at a time** (for example, swap with the space bar).
- The two cubes **merge** back into a 1×1×2 block when they are on adjacent cells.
- A single cube can trigger a soft switch, but **cannot** trigger a heavy switch and **cannot** finish the stage.

## 3. General requirements
- Source code in **Python**.
- Helper libraries (GUI, data structures) are allowed, but **the search algorithms must be implemented by the team**.
- Code organisation is free, but it must be professional and clear.

## 3.1 Re-implementing the game (20 points)
**A GUI is mandatory** (web or desktop).

**Core mechanics (10 pts):** a board with floor, void and goal cells; a 1×1×2 block with 3 orientations; 4 rolls with correct orientation changes; detection of illegal moves (off the board / over a void); detection of a win (block standing on the goal).

**Advanced tiles (10 pts):** fragile tiles, bridges, all 3 switch kinds (soft, heavy, split, including splitting/merging the block and both bridge effects). **The solvers must also handle these tiles correctly.**

Notes (F.Y.I.):
- Implement and unit-test the orientation transition table early: every (orientation, direction) pair maps deterministically to a new (orientation, position).
- **The state must include the open/closed status of every bridge**, not only the block's position and orientation. The same block position with a different bridge configuration is a **different state**.
- You may design your own stages or rebuild classic ones. Provide a **simple text/JSON format** for loading stages, shared by every solver.

The GUI must show the basic controls (New Game, Restart, a button for each solver).

## 3.2 BFS solver (10 pts)
- Implement a solver using **Breadth-First Search**.
- Record **Search Time, Memory Usage, Expanded Nodes and Solution Length** for the experiments. The other solvers record the same.

## 3.3 DFS solver (10 pts)
- Implement **Depth-First Search**. **Iterative Deepening Search (IDS)** may be used instead, but this must be stated in the report.
- Handle repeated states to avoid infinite loops (visited set, hashing, ...).

## 3.4 UCS solver (10 pts)
- Implement **Uniform-Cost Search**.
- **In the report**: define and justify the **cost function** clearly. For example each roll costs 1, or costs differ (rolling onto a fragile tile is "expensive" because it is risky, pressing a switch is "cheap"), as long as it is explained sensibly.
- If every move costs 1 then UCS = BFS; only a **non-uniform** cost function with an intuitive explanation makes this part meaningful.

## 3.5 A* solver (10 pts)
- Implement **A\*** with a **suitable heuristic** that estimates how close the state is to the goal.
- Heuristic ideas (not mandatory):
  - Manhattan distance from the block to the goal divided by 2 (one roll moves at most 2 cells).
  - An orientation term: if the block is not standing it needs at least 1 more roll to stand on the goal, plus a small penalty.
  - A relaxed "point-object" distance: ignore orientation and the void/fragile constraints, treat the block as a point on a 4-connected grid, and use the shortest path to the goal as a lower bound.
- **In the report**:
  - Explain how the heuristic was designed.
  - Discuss whether the heuristic is **admissible** (never overestimates the true remaining cost) and/or **consistent**, with a clear argument. The heuristic must be admissible **under the cost function you chose**.

## 3.6 Report (30 points)
A well-formatted **PDF** containing:

**Project Planning and Task Distribution**
- Each member's responsibilities: the tasks assigned and the **completion percentage**.
- Example: the group scores 9.0 and member A completed 90%, so A's score is 9.0 × 90% = 8.1.
- Contributions must be assessed **fairly and accurately**.

**Algorithm Description (10 pts)**
- Explain each algorithm in detail (BFS, DFS/IDS, UCS, A*).
- Describe how the problem is formalised: state representation (including orientation and bridge configuration), actions, transition model, goal test, cost function, heuristic, and how revisiting states is avoided.

**Experiments (20 pts)**
- Evaluate performance on many test cases (**a fixed test set**, so the algorithms are compared fairly). Tests may be grouped by difficulty (no advanced tiles; with fragile tiles; with switches; both combined), and the groups must be described clearly.
- For each algorithm measure: search time, memory (peak), expanded nodes, solution length (number of moves).
- Present: a summary **table**, **charts** comparing the algorithms, and **comments** on each algorithm's strengths and weaknesses.

**References and Appendix**
- List every reference (papers, books, tutorials, GitHub repos, ...).
- Appendix, for example: how Generative AI (LLMs) was used in the work, and the prompts used.

## 3.7 Video (10 points)
Upload a demo video to **YouTube** and put a **public link** in the report.

**Graphical Interface (5 pts):**
- Demo of the program's GUI.
- Show the layout clearly: the board with every tile kind (floor, void, goal, fragile, switch/bridge), the block in its orientations, the controls (New Game, Restart, Solve BFS/DFS/UCS/A*).

**Feature Presentation (5 pts):**
- Manual play: rolling the block, triggering switches, winning/losing a stage.
- Running solvers (choose a stage, run BFS/UCS/A*, show the solution, optionally animate or replay the moves).

The video needs **subtitles or narration** (English or Vietnamese).

## 4. Submission
- Submit the **source code + report** as an archive (.zip, .rar) named `StudentID1_StudentID2_...`.
- If the archive is larger than **20MB**, upload it to Google Drive and share the link.
- **Nothing may be changed after the deadline.**

Sample folder structure:
```
StudentID1_StudentID2_...
├── Source
│   ├── main.py
│   ├── README.md          (how to run the code)
│   ├── requirements.txt   (libraries to install)
│   └── ...
└── Report.pdf             (with the demo video URL)
```

## 5. Notes
- This is a **GROUP** assignment.
- Duration: about 3 weeks.
- AI tools are **not forbidden**, but should be used sensibly. The lab instructor may hold random oral checks with any group to test their understanding of the project.
- Any form of plagiarism, cheating or breach of academic integrity scores **0 for the whole course**.

## Score summary
| Item | Points |
|---|---|
| Game: core mechanics | 10 |
| Game: advanced tiles | 10 |
| BFS solver | 10 |
| DFS solver | 10 |
| UCS solver | 10 |
| A* solver | 10 |
| Report (Algorithm Description 10 + Experiments 20) | 30 |
| Video (GUI 5 + Features 5) | 10 |
