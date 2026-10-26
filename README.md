# Bloxorz Solver

A playable Python re-implementation of the block-rolling puzzle Bloxorz, plus search-based solvers (BFS, DFS/IDS, UCS, A*) that solve any stage and replay the solution in the GUI.

Course project for CSC14003 – Introduction to Artificial Intelligence, VNU-HCM.

## Features
- Core mechanics: standing / lying blocks, four rolling directions, void and goal cells
- Advanced tiles: fragile tiles, bridges, soft / heavy / split switches, block splitting
- Free Play modes: Normal and Advanced, with tutorial stages for each advanced mechanic
- Solvers with metrics: search time, peak memory, expanded nodes, solution length
- Stages loaded from JSON

## Getting started
See [`Source/README.md`](Source/README.md) for setup, run and test instructions.

## Docs
- [`docs/UI_ENGINE_INTERACTION.md`](docs/UI_ENGINE_INTERACTION.md) – UI and engine interface
- [`docs/ALGORITHM_IMPLEMENTATION_GUIDE.md`](docs/ALGORITHM_IMPLEMENTATION_GUIDE.md) – state representation and algorithm contract
- [`docs/SOLVER_IMPLEMENTATION.md`](docs/SOLVER_IMPLEMENTATION.md) – solver algorithms, metrics, and testing guide
- [`docs/ADVANCED_MECHANICS.md`](docs/ADVANCED_MECHANICS.md) – fragile tiles, bridges, switches, and split mechanics
- [`docs/YEU_CAU_DE_BAI.md`](docs/YEU_CAU_DE_BAI.md) – assignment requirements
- [`docs/PHAN_CONG.md`](docs/PHAN_CONG.md) – task split
- [`docs/AI - Project 1.pdf`](docs/AI%20-%20Project%201.pdf) – project brief
