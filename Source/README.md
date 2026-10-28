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

```bash
.venv/Scripts/python -m pytest   # Windows
.venv/bin/python -m pytest       # macOS / Linux
```

## Documentation

- [UI and engine interaction](../docs/UI_ENGINE_INTERACTION.md)
- [Advanced mechanics](../docs/ADVANCED_MECHANICS.md)
- [Algorithm implementation guide](../docs/ALGORITHM_IMPLEMENTATION_GUIDE.md)
- [Solver implementation guide](../docs/SOLVER_IMPLEMENTATION.md)
