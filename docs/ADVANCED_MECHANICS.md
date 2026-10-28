# Bloxorz Advanced Mechanics

This document specifies the advanced Bloxorz gameplay rules: fragile tiles,
bridges, switches, and block splitting/merging. It also defines the state and
solver requirements needed to handle these mechanics correctly.

## Terminology

- **Full block** — the normal `1 x 1 x 2` block.
- **Standing** — the full block occupies one cell.
- **Lying** — the full block occupies two adjacent cells.
- **Split cube** — a `1 x 1 x 1` unit cube created by a split switch.
- **Bridge state** — the open/closed status of every bridge on the board.
- **Supporting tile** — a tile that can hold the part of the block resting on it
  under the conditions described below.

## 1. Fragile Tiles

**Visual identifier:** orange tile.

**Weight constraint:** a fragile tile supports the block only when the block's
weight is distributed across two cells.

**Failure condition:** if the full `1 x 1 x 2` block is standing upright on a
fragile tile, the tile breaks, the block falls, and the move is illegal.

**Safe cases:**

- A lying full block may occupy a fragile tile; the weight is distributed.
- A split `1 x 1 x 1` cube may rest on a fragile tile; its weight is half that
  of the standing full block.

Fragile tiles never change state permanently. The condition is evaluated for
the block configuration at the end of the move.

## 2. Bridges

**Function:** a bridge is a dynamic tile whose passability is controlled by one
or more switches.

**Open bridge:** behaves exactly like a normal solid floor tile. The block may
stand on it or lie across it.

**Closed bridge:** behaves exactly like a void cell. If any occupied cell of the
block is on a closed bridge after a move, the block falls and the move is
illegal.

**Linkage:** each switch is linked to one or more specific bridge tiles. A
switch activation updates all of its linked bridges.

Bridge state is part of the game state. Two block placements are different
states when their bridge configurations differ.

## 3. Switches

### 3.1 Switch types and activation conditions

#### Soft switch (octagon / circle)

Activated when any part of the block presses the switch, regardless of
orientation.

Valid activators:

- standing full block
- lying full block, with either half on the switch
- a single split cube

#### Heavy switch (X-shaped)

Activated only when the full weight of the block presses the switch.

Valid activator:

- standing full block only

Invalid activators:

- lying full block, even if one half covers the switch
- a single split cube

#### Split switch (bracket-shaped `()`)

Activated only when a standing full block lands upright on it.

Effect: the full block is immediately split into two `1 x 1 x 1` cubes and
teleported to the two predefined target coordinates for that switch. If those
target cells are horizontally or vertically adjacent, the cubes merge back into
a lying `1 x 1 x 2` block immediately.

Invalid activators:

- lying full block
- a single split cube

### 3.2 Bridge-control behavior

Every soft or heavy switch operates in one of two modes.

#### Toggle mode

Each activation flips the state of every linked bridge:

- open becomes closed
- closed becomes open

#### Permanent mode

Each activation sets every linked bridge to a fixed target state, for example
permanently open or permanently closed. Later activations have no further
effect.

A switch may affect several bridges, and a bridge may be linked to more than one
switch. The resulting bridge configuration is evaluated after all activation
effects for the move have been applied.

## 4. Block splitting and merging

### 4.1 Split state

When split, the block becomes two independent `1 x 1 x 1` cubes. Each cube
occupies one cell.

### 4.2 Movement

Only one cube moves per turn. A move shifts the active cube by one adjacent cell
in one of the four cardinal directions: up, down, left, or right.

The other cube remains stationary.

### 4.3 Manual control

The player must be able to switch control between the two cubes at any time,
for example with the spacebar. Switching control does not move either cube.

### 4.4 Switch interactions while split

- A split cube **can** activate a soft switch.
- A split cube **cannot** activate a heavy switch.
- A split cube **cannot** activate a split switch.

### 4.5 Goal interactions while split

A split cube may safely rest on the goal tile, but it cannot complete the stage.
The stage is won only by a full block standing upright on the goal.

### 4.6 Merging

Whenever the active cube moves onto a cell that is horizontally or vertically
adjacent to the other cube, the two cubes immediately merge back into a single
lying `1 x 1 x 2` block. The merged block occupies those two cells.

The merge happens automatically as part of the same move. The orientation of
the merged block is determined by how the two cubes are adjacent:

- adjacent horizontally: horizontal lying block
- adjacent vertically: vertical lying block

The same immediate merge applies to split-switch teleport targets: if the two
configured cube cells are adjacent, the split resolves directly into a lying
whole block. Same-cell targets are invalid.

## 5. Solver and state requirements

### 5.1 Full support rule

In every state, whether whole or split, every cell occupied by the block or by
a unit cube must be supportable:

- standard floor: always supported
- open bridge: supported
- closed bridge: not supported
- soft switch, heavy switch, or split tile: supported as floor
- goal tile: supported, but only a full standing block wins
- fragile tile: supported only when the full block is lying, or when the
  occupying piece is a split cube

Every illegal move due to lack of support is a falling move. It is not a valid
successor state for the solver.

### 5.2 State uniqueness

A game state is uniquely defined by:

1. whether the block is whole (`1 x 1 x 2`) or split into two `1 x 1 x 1` cubes
2. either:
   - the coordinates and orientation of the full block, or
   - the coordinates of both split cubes
3. the open/closed status of every bridge on the board

State equality, hashing, and visited-set membership must include all bridge
states. A move that changes only bridge states still produces a different
state.

When modeling split play in a search algorithm, the identity of the active cube
must also be tracked or encoded so that a move is applied to the intended cube.
Changing active control is a control operation, not a spatial move.

### 5.3 Successor generation

For each candidate action, successor generation should:

1. compute the new block or active-cube placement
2. determine which switches are activated by the new placement
3. apply all toggle or permanent bridge effects
4. validate every occupied cell against the resulting bridge configuration
5. reject the move if any occupied cell is unsupported
6. apply fragile-tile failure conditions
7. apply split-switch teleportation and block splitting if activated
8. apply automatic merging if the split cubes become adjacent
9. return the resulting state only if the move is legal

Bridge updates must be applied before final support validation.

### 5.4 Goal test

The goal test succeeds only when:

- the block is not split, and
- the full block is standing upright on the goal cell

A lying block that covers the goal does not win. A split cube on the goal does
not win.

### 5.5 Cost and search notes

- Legal moves may have different costs if the cost model distinguishes risky or
  switch-related moves. The chosen cost function must be documented.
- Heuristics used by A* must remain admissible with respect to that cost
  function.
- The solver must include bridge configuration and split status in the visited
  state key.
- Duplicate detection must not collapse states that differ only in bridge
  configuration or split-cube placement.

## 6. Advanced-mode tutorial stages

Advanced Free Play begins with four tutorial stages:

| Level | Introduces |
| --- | --- |
| 54 | Fragile tiles: cross them with a lying block |
| 55 | Closed bridges and soft switches |
| 56 | Heavy switches: stand upright to activate |
| 57 | Split switches, cube control, and merging |

Each tutorial shows an in-game text guide explaining the mechanic, and the same
tip appears in the Free Play menu. After these tutorials, Advanced mode
continues with the advanced stages from the main level set.

## 7. Implementation checklist

- [ ] Fragile tile breaks under a standing full block.
- [ ] Fragile tile supports a lying full block.
- [ ] Fragile tile supports a split cube.
- [ ] Closed bridge behaves as void.
- [ ] Open bridge behaves as normal floor.
- [ ] Soft switch activates for standing, lying, and split-cube contact.
- [ ] Heavy switch activates only for a standing full block.
- [ ] Split switch activates only for a standing full block and teleports two cubes.
- [ ] Toggle switches flip all linked bridges.
- [ ] Permanent switches set all linked bridges to their fixed state.
- [ ] Only the active split cube moves each turn.
- [ ] Control can be switched between split cubes without moving either.
- [ ] Adjacent split cubes merge automatically into a lying full block.
- [ ] Adjacent split-switch teleport targets merge immediately.
- [ ] Split cubes cannot win by entering the goal.
- [ ] Bridge configuration is part of state equality and hashing.
- [ ] All occupied cells are validated after switch effects are applied.
