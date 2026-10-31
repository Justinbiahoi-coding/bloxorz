# Bloxorz Solver

A playable Python re-implementation of the block-rolling puzzle Bloxorz, plus search-based solvers (BFS, DFS, UCS, A*) that solve stages and replay their solutions in the GUI.

Course project for CSC14003 – Introduction to Artificial Intelligence, VNU-HCM.

## Features
- Core mechanics: standing / lying blocks, four rolling directions, void and goal cells
- Advanced tiles: fragile tiles, bridges, soft / heavy / split switches, block splitting
- Free Play modes: Normal and Advanced, with tutorial stages for each advanced mechanic
- 2D and 3D front-ends; the 3D front-end includes Tower and Free Play
- Solvers with metrics: search time, peak memory, expanded nodes, solution length
- Stages loaded from JSON

## Getting started
See [`Source/README.md`](Source/README.md) for setup, run and test instructions.

## Docs
- [`docs/UI_ENGINE_INTERACTION.md`](docs/UI_ENGINE_INTERACTION.md) – UI and engine interface
- [`docs/ALGORITHM_IMPLEMENTATION_GUIDE.md`](docs/ALGORITHM_IMPLEMENTATION_GUIDE.md) – state representation and algorithm contract
- [`docs/SOLVER_IMPLEMENTATION.md`](docs/SOLVER_IMPLEMENTATION.md) – solver algorithms, metrics, and testing guide
- [`docs/UI3D_SPEC.md`](docs/UI3D_SPEC.md) – 3D UI specification, design system and screens
- [`docs/ADVANCED_MECHANICS.md`](docs/ADVANCED_MECHANICS.md) – fragile tiles, bridges, switches, and split mechanics
- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md) – assignment requirements
- [`docs/TASK_SPLIT.md`](docs/TASK_SPLIT.md) – task split
- [`docs/AI - Project 1.pdf`](docs/AI%20-%20Project%201.pdf) – project brief
