# Bloxorz

## Requirements

- Python 3.10 or newer ([python.org](https://www.python.org/downloads/); on Windows tick "Add python.exe to PATH")
- Internet on the first run only, to download the libraries

Nothing else needs to be installed by hand.

## Run

Double-click a launcher in this folder:

| | Windows | macOS |
|---|---|---|
| 2D (Pygame) | `Play 2D.bat` | `Play 2D.command` |
| 3D (Ursina / Panda3D) | `Play 3D.bat` | `Play 3D.command` |

or from a terminal in this folder:

```bash
python main.py      # 2D
python main3d.py    # 3D
```

(`python3` on macOS / Linux.)

The first run creates a private environment in `.venv/` and installs `requirements.txt`
into it (about 1-3 minutes); later runs start at once. Your system Python is left untouched.
The libraries are reinstalled automatically only when `requirements.txt` changes.

If macOS refuses to open a `.command` file, right-click it and choose **Open** once.

### Manual setup (optional)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
.venv/bin/python -m pip install -r requirements.txt       # macOS / Linux
```

The game uses `pygame-ce` and `pygame-menu-ce` (drop-in forks, still `import pygame` /
`import pygame_menu`) because they ship ready-made wheels for every current Python,
including 3.14. `ursina` is pinned to 5.2.0: newer versions change the font API.

## The 3D game

The opening film plays once (any key skips it) and stops on the title over the tower doors, where
the main menu sits:

- **Tower** — the climb: ten floors from the lobby to the roof, one elevator ride between them.
- **Free Play** — any single stage. *Normal* starts with four tutorials (fragile tiles, bridges,
  heavy switches, split cubes), then levels 1–23; *Advanced* holds level 24 and up. Cleared stages
  are marked.
- **Algorithms** — pick a stage and a solver (BFS, DFS, UCS, A*, IDS), run it from the stage start
  and read the time, peak memory, expanded nodes and solution length; *Run all* compares every
  solver on the same stage. Replay the solution, or watch the expanded nodes light up the board.
- **Settings** — music volume, move speed, fullscreen, key hints, tile legend; saved in
  `settings.json` next to the game.

In a game the toolbar at the top right has **New Game**, **Restart**, **Hint** (a ghost block on
the next best position) and **Solve** (pick a solver; it plays the remaining moves from where you
stand, and any key takes the controls back).

| Key | Action |
|---|---|
| Arrow keys | Roll the block |
| Space | Switch the active cube when the block is split |
| R | Restart the level / floor |
| H | Hint |
| Esc | Pause (Resume, Restart, New Game, Settings, Main Menu) |
| F | Fullscreen |
| Enter | Confirm in menus |

## Test

```bash
.venv/Scripts/python -m pytest   # Windows
.venv/bin/python -m pytest       # macOS / Linux
```

## Documentation

- [UI and engine interaction](../docs/UI_ENGINE_INTERACTION.md)
- [Advanced mechanics](../docs/ADVANCED_MECHANICS.md)
- [Algorithm implementation guide](../docs/ALGORITHM_IMPLEMENTATION_GUIDE.md)
- [Solver implementation guide](../docs/SOLVER_IMPLEMENTATION.md)
- [3D UI specification](../docs/UI3D_SPEC.md) and [screenshots](../docs/ui3d_screens/)
