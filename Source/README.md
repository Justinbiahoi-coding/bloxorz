# Bloxorz

## Setup

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt

## Run

2D front-end:

    python main.py

3D front-end:

    python main3d.py

The 3D front-end uses the pinned Ursina version in `requirements.txt`.

## Free Play

Free Play offers two level sets in both front-ends:

- **Normal** — stages without advanced tiles.
- **Advanced** — starts with tutorials for fragile tiles, bridges, heavy switches, and split cubes, followed by the advanced stages.

3D Free Play controls:

- Arrow keys — roll
- Space — switch active split cube
- R — restart level
- Esc — return to menu
- F — toggle fullscreen

## Test

    pytest

## Documentation

- [UI and engine interaction](../docs/UI_ENGINE_INTERACTION.md)
- [Advanced mechanics](../docs/ADVANCED_MECHANICS.md)
- [Algorithm implementation guide](../docs/ALGORITHM_IMPLEMENTATION_GUIDE.md)
- [Solver implementation guide](../docs/SOLVER_IMPLEMENTATION.md)
