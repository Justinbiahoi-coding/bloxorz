# 3D UI redesign specification

## 1. Features from `feat/advanced-mechanisms`

Only the interface changes; no feature is dropped.

| # | Feature (`feat/advanced-mechanisms`) | Screen that now handles it |
|---|---|---|
| Y1 | Main menu: Tower, Free Play, Algorithms, Exit | Main Menu |
| Y2 | Free Play in two modes: **Normal** (tutorials 54–57 first, then levels 1–23) / **Advanced** (level 24 and up) | Level Select |
| Y3 | Level choice: Prev/Next, ←/→ keys, Enter/Space to start, Esc to go back | Level Select |
| Y4 | Tutorial names and a tip for each tutorial | Level Select + HUD |
| Y5 | "Loading…" screen while a stage is built | Loading |
| Y6 | Free Play controls: arrows roll, Space switches cube when split, R restarts, Esc pauses, F fullscreen, one move buffered while rolling | Gameplay + HUD |
| Y7 | Falling effect when rolling off the board | Gameplay (now the same game-over scene as the Tower) |
| Y8 | Result screen: Next Level (when there is one), Retry, Main Menu; keys N / R / Enter / Esc | Result |
| Y9 | Go to the next stage in the same mode (`next_level`) | Result |
| Y10 | Tower: intro, elevator cutscene, zombies, game over, R to retry | Kept as is, only the HUD changes |
| Y11 | Engine logic: `attempt_move` (moved/won/fell), `catalog.py`, advanced-tile fixes | Used as is |

## 2. 2D features the 3D version must have

| # | 2D feature | 3D status before the redesign |
|---|---|---|
| D1 | Algorithms: choose mode, stage, algorithm | Only a "not available" message |
| D2 | Solver result: time, nodes explored, solution cost | Missing |
| D3 | Replay the solution (S) | Missing |
| D4 | Replay the order nodes were explored (N) | Missing |
| D5 | Run the solver again (R) | Missing |
| D6 | Move hint (H, uses UCS; disabled in 2D) | Missing, to be added |

## 3. Check against the brief (whole PDF re-read)

| Brief section | Requirement | Before | Done in the 3D UI |
|---|---|---|---|
| 3.1 | GUI shows the board: floor, void, goal, fragile, switch, bridge | ✅ `floor.py` | Legend of the tile kinds |
| 3.1 | Block with 3 orientations, 4 rolls, illegal-move detection, win | ✅ | — |
| 3.1 | Split/merge, switch cube with Space | ✅ | Active cube shown on the HUD; Space hint only on split stages |
| 3.1 | **New Game, Restart and solver buttons** | ❌ keys only | In-game toolbar: New Game, Restart, Hint, Solve BFS/DFS/UCS/A* |
| 3.1 | Stages loaded from JSON, shared by every solver | ✅ | — |
| 3.2–3.5 | Each solver records **time, peak memory, expanded nodes, solution length** | ⚠️ no memory | All 4 metrics shown (peak memory added to the engine, see section 4) |
| 3.3 | DFS or IDS | DFS ✅, IDS ❌ | IDS shown as "not implemented" instead of crashing |
| 7 (video) | Manual play: roll, trigger switches, win/lose | ✅ | — |
| 7 (video) | Choose a stage, run BFS/UCS/A*, show the solution, **animate/replay** | ❌ | Solution replayed on the 3D block, with play/pause/step |
| 7 (video) | Clear view of the interface, tile kinds and controls | — | Legend + toolbar |

## 4. Outside the UI, but the UI depends on it

These belong to the solver/engine owners. The UI copes safely while they are missing.

| Issue | Effect | Proposal |
|---|---|---|
| **Peak memory** not measured | Required by the brief | Done: `tracemalloc` in `solve_problem` (`engine/solver.py`), returned as `peak_memory_kb` in `SolveResult` |
| **IDS** missing | The "Iterative DFS" entry would crash | The UI catches `NotImplementedError` and shows "Not implemented" |
| **UCS** uses cost 1 per step, so its results equal BFS | The brief says uniform cost makes UCS meaningless | The solver owner defines a separate `path_cost` |
| `explored` holds `State` for DFS/A* but `Node` for BFS/UCS | Counts are still correct; the UI reads both | Better to agree on one type |

Timings on the test machine: the slowest is DFS on level 43, 0.67 s. The longest solution is 106 moves (BFS, level 46). Peak memory is about 6 MB. No background thread is needed, only a "Solving…" panel.

## 5. Design system

Visual direction (reviewed 28/10): an **elevator control panel** in a low-poly city. Rectangular buttons with slightly chamfered corners, charcoal/blue-grey faces, with depth (the face sits on a dark edge and sinks when pressed). Warm gold is reserved for the main action and the selected item. Source: `ui3d/theme.py`. Samples: `docs/ui3d_screens/ui3d_widgets_preview.png`, `docs/ui3d_screens/01_menu.png`.

### Main colours

| Token | RGB | Used for |
|---|---|---|
| `FACE` / `FACE_HOVER` / `FACE_PRESS` | 38,43,52 / 52,59,71 / 29,33,40 | Secondary button face by state |
| `EDGE`, `RIM` | 15,17,22 · 74,81,95 | Bottom edge (depth), outline |
| `GOLD` / `GOLD_HOVER` / `GOLD_PRESS` | 240,182,74 / 250,202,108 / 196,146,56 | Main button, selected item |
| `GOLD_RIM` | 255,214,128 | Focus ring |
| `PANEL`, `PANEL_RIM` | 21,24,30 a236 · 62,68,80 | Panels |
| `DONE_FACE`, `GREEN` | 46,68,52 · 150,212,150 | Completed level |
| `OFF_FACE`, `OFF_TEXT` | 64,68,76 · 118,122,130 | Disabled, locked level |
| `ORANGE` | 255,146,96 | Warning text (danger buttons) |
| `TEXT`, `MUTED`, `INK` | 236,232,224 · 150,156,168 · 34,26,14 | Body text, secondary text, text on gold |

### Type
Fredoka is a variable font, and Panda3D only reads its Light (300) instance, so the text came out thin. `tools/make_font_weights.py` cuts 3 static weights:
- `Fredoka-BoldCondensed` (700, width 80): titles, big numbers.
- `Fredoka-SemiBold` (600): buttons, labels, key hints.
- `Fredoka-Medium` (500): body text, the default font of the 3D version.

Each font has one fixed glyph resolution (`theme.RESOLUTION`) so large titles stay sharp, and keeps its glyphs once drawn (`widgets.keep_glyphs`).

Fredoka has **no** `← ↑ → ↓ ▶ ■ ✓ ⏸`; these icons are drawn as meshes in `ui3d/icons.py`.

### Components (`ui3d/widgets.py`)
- `UIButton`: kinds `primary` / `secondary` / `quiet` (text-only links such as Back) / `danger`; 5 states: normal, hover, focus (gold ring + pointer), pressed (sinks), disabled. Labels shrink so they are never cut off.
- `back_button`, `icon_button` (pause, restart), `Stepper`, `Tabs`.
- `LevelTile`: completed (green + check), selected (gold ring and number), available, locked (dim + padlock, cannot be chosen).
- `Slider` (drag, click, or ←/→), `Checkbox`, `ProgressBar`.
- `Panel`, `Modal`, `ConfirmDialog` (Esc cancels, Enter confirms; for danger dialogs the default focus is Cancel).
- `HUDBar` (compact strip at the top left), `KeyHint`, `StatCard`, `Toast` (several toasts stack, never overlap).
- `FocusGroup`: keyboard control for all of the above, including the level grid.

### Interaction and checks
- Mouse and keyboard work on every screen: ↑/↓ (or ←/→) to choose, Enter to press, Esc to go back.
- The in-game HUD stays at the screen edges and does not cover the board. Algorithm metrics appear only in the Algorithms mode.
- Every screen is checked by screenshot at 1280×720 and 1920×1080.

## 6. Screens

In-game text stays in English, as in the existing version.

### 6.1 Main Menu (= the last shot of Justin's intro)
Flow: launch → Loading → Justin's intro (any key skips) → stops on the last shot: the BLOXORZ TOWER title over the tower doors. The menu panel stands at the lower right, where the old "Enter Building" button was.

- **Tower:** continues Justin's sequence, the bin rolls into the lobby.
- **Free Play / Algorithms / Settings:** open the matching screen.
- **Exit / Esc:** confirmation dialog.
- **Back to the menu after playing:** the scene is rebuilt and goes straight to the last shot, without replaying the whole intro.

Code: `ui3d/app.py` (`main_menu`, `_enter_tower`), `ui3d/screens/main_menu.py`. The only changes to Justin's code are:
- `TowerGame.menu_hold`: holds the intro on the title shot while the menu is open.
- `Intro.show_button`, `Intro.at_title`.
- The intro title uses the BoldCondensed font, with "TOWER" in gold.
- `Intro.step` clamps dt so the intro does not jump ahead when the game stalls while loading.
- The vignette and grain overlays scale with the real window aspect ratio.

### 6.2 Level Select (shared by Free Play and Algorithms)
```
  FREE PLAY                                  [ Normal | Advanced ]
  ┌─────────────────────────┐   ┌──────────────────────────────┐
  │   ‹   Tutorial 1  ›     │   │                              │
  │        Fragile          │   │   (3D preview of the stage)  │
  │  tiles: ■fragile ■bridge│   │                              │
  │  "Fragile tiles break…" │   └──────────────────────────────┘
  │  [ Start ]   [ Back ]   │
  └─────────────────────────┘
```
Built as a grid of level tiles with an info panel; it always stands over the title shot, also when opened from a finished game.

### 6.3 Gameplay HUD (Free Play and Tower)
```
 ┌ Tutorial 1 – Fragile ┐                [New] [Restart] [Hint] [Solve ▾] [❚❚]
 │ MOVES 12   ACTIVE: A │
 └──────────────────────┘
          ┌ Fragile tiles break under a standing block… ┐   ← tip, does not cover the stage name
                                          ┌ legend ┐
                                          │■ floor ■ fragile ■ switch ■ bridge ■ goal│
   ←↑↓→ roll   Space switch cube   R restart   H hint   Esc pause
```
`Solve ▾` opens a list of BFS / DFS / UCS / A*. Choosing one solves from the current state and replays the solution right on the stage being played. In Free Play the New Game button is called **Levels** (it returns to Level Select). The Space hint appears only on stages with a split switch.

### 6.4 Pause (Esc)
Resume, Restart, New Game (Tower) or Level Select (Free Play), Settings, Main Menu.

### 6.5 Result
Win: LEVEL CLEARED, number of moves, and "best possible N" from BFS. Buttons Next / Retry / Level Select / Main Menu.
Lose: the Tower's game-over scene (the dead close in on the bin, GAME OVER over the cat); R retries, Esc goes to Level Select in Free Play or the menu in the Tower.

### 6.6 Algorithms Lab (the largest new part)
```
  ALGORITHMS                                           [ Normal | Advanced ]
  ┌ Setup ───────────────┐  ┌──────────────────────────────────────────┐
  │ Level   ‹ Level 12 › │  │                                          │
  │ Algo  [BFS][DFS][UCS]│  │        3D view of the stage, the block    │
  │       [A*][IDS]      │  │        replaying the solution             │
  │ [ Run ]  [ Run all ] │  │                                          │
  └──────────────────────┘  │  ▶❚❚  ⏮ ⏭   speed ‹1x›   step 14/31     │
  ┌ Result: BFS ─────────┐  └──────────────────────────────────────────┘
  │ 12.4 ms   3.1 MB     │  ┌ Compare (Run all) ───────────────────────┐
  │ 812 nodes 31 moves   │  │ algo  time   memory  expanded  length    │
  │ [Replay] [Explored]  │  │ BFS   12ms   3.1MB   812       31        │
  └──────────────────────┘  │ A*    4ms    1.2MB   205       31  ▇▇    │
                            └──────────────────────────────────────────┘
```
- **Run**: runs one algorithm and shows the 4 metrics the brief asks for.
- **Run all**: runs all 4 on the same stage and shows a comparison table with horizontal bars. Useful for the experiments and the video.
- **Replay**: the 3D block rolls through the solution. **Explored**: highlights the explored cells in order.
- The Lab offers all 57 stages, split into Normal and Advanced like Free Play.

### 6.7 Settings
Music volume, block roll speed, fullscreen, show/hide the key hints, show/hide the legend, clear Free Play progress. Saved to `settings.json` next to the game and kept between launches.

## 7. Code layout

```
ui3d/
  theme.py        colours, type sizes, animation timings
  widgets.py      Panel, UIButton, Stepper, Tabs, Checkbox, Slider, StatCard, KeyHint, Toast, Modal
  hud.py          HUD + toolbar shared by Free Play and the Tower
  death.py        game-over scene shared by Free Play and the Tower
  loadfast.py     cached model lookups (Ursina rescans the asset folder on every load)
  screens/
    main_menu.py  level_select.py  dialogs.py  settings_screen.py  loading.py  algorithms.py
  autoplay.py     plays a list of moves on the existing Floor + Block (Solve, replay)
  app.py          screen state machine (replaces the old App3D)
  free_play.py    keeps the play logic, uses the new HUD/Modal
```
`game.py` (Tower), `floor.py`, `block.py` and the scenery, intro and zombies: only the HUD changes, the graphics are untouched (except that Free Play and the Lab now use the tower's furnished storey with the lift at the goal).

## 8. Build order

1. `theme.py` + `widgets.py`, each component checked by screenshot.
2. Main Menu, Level Select, Loading, Settings.
3. HUD + toolbar + Pause + Result, applied to Free Play, then the Tower.
4. Replay + Solve in game.
5. Algorithms Lab: Run, Run all, Replay, Explored.
6. Full pass with keyboard and mouse, tests, a screenshot of every screen.
