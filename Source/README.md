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

If macOS refuses to open a `.command` file, right-click it and choose **Open** once. If it says
you do not have permission (an unzipped copy can lose the executable flag), run
`chmod +x "Play 2D.command" "Play 3D.command"` in this folder once, or use `python3 main3d.py`.

On Windows, keep the folder at a short path (for example `C:\Bloxorz` or straight in Downloads):
if the setup stops with *"The filename or extension is too long"* (WinError 206), the path is over
Windows' 260-character limit; move the folder, delete `.venv` and run again.

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
- **Algorithms** — pick a stage and a solver (BFS, DFS, UCS, A*), run it from the stage start
  and read the time, peak memory, expanded nodes and solution length; *Run all* compares every
  solver on the same stage. Replay the solution, or watch the expanded nodes light up the board.
- **Settings** — music volume, move speed, fullscreen, key hints, tile legend; saved in
  `settings.json` next to the game.

In a game the toolbar at the top right has **New Game** (called **Levels** in Free Play: back to
the level select), **Restart**, **Hint** (a ghost block on the next best position) and **Solve**
(pick a solver; it plays the remaining moves from where you stand, and any key takes the controls
back).

| Key | Action |
|---|---|
| Arrow keys | Roll the block |
| Space | Switch the active cube when the block is split |
| R | Restart the level / floor |
| H | Hint |
| Esc | Pause (Resume, Restart, New Game, Settings, Main Menu) |
| F | Fullscreen |
| Enter | Confirm in menus |

## The 2D game

`main.py` opens the Pygame version: the same stages and solvers in a flat view. Arrows roll,
Space switches cube, H shows a hint and Esc goes back; on the result screen R retries and N or
Enter goes to the next stage.

## Test

```bash
.venv/Scripts/python -m pytest   # Windows
.venv/bin/python -m pytest       # macOS / Linux
```

## Experiments

`benchmark.py` runs the four solvers on the fixed test set of 18 stages used in the report
(groups: simple, fragile, switches and bridges, combined) and saves `benchmark_results.json`;
`plot_charts.py` draws the comparison charts from that file (matplotlib, installed with the rest):

```bash
.venv/Scripts/python benchmark.py      # Windows (.venv/bin/python on macOS / Linux)
.venv/Scripts/python plot_charts.py
```

## Documentation

The design notes are in the `docs/` folder of the project repository:

- [UI and engine interaction](https://github.com/Justinbiahoi-coding/bloxorz/blob/main/docs/UI_ENGINE_INTERACTION.md)
- [Advanced mechanics](https://github.com/Justinbiahoi-coding/bloxorz/blob/main/docs/ADVANCED_MECHANICS.md)
- [Algorithm implementation guide](https://github.com/Justinbiahoi-coding/bloxorz/blob/main/docs/ALGORITHM_IMPLEMENTATION_GUIDE.md)
- [Solver implementation guide](https://github.com/Justinbiahoi-coding/bloxorz/blob/main/docs/SOLVER_IMPLEMENTATION.md)
- [3D UI specification](https://github.com/Justinbiahoi-coding/bloxorz/blob/main/docs/UI3D_SPEC.md)
