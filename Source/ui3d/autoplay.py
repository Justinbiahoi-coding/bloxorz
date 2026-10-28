"""Solve from where the player stands and play the moves, and show a hint as a ghost block.

Both work on any scene with .session, .floor, .phase and .input(key) (Free Play and the Tower): the
moves go in as the same key presses a player would make, so the roll animation, switches, splits
and winning all happen exactly as in normal play.
"""
from ursina import Entity, color, destroy, time

from engine import solve_problem
from .floor import TILE_TOP

ACTION_KEYS = {'LEFT': 'left arrow', 'RIGHT': 'right arrow', 'DOWN': 'up arrow', 'UP': 'down arrow',
               'SWITCH': 'space'}
PLAYER_KEYS = set(ACTION_KEYS.values()) | {'r'}


def solve_from(session, algorithm):
    """(moves, result, error) solving from the session's current state; error is a short message or None."""
    try:
        result = solve_problem(session.problem, algorithm, initial=session.state)
    except NotImplementedError:
        return None, None, '{} is not implemented yet'.format(algorithm)
    if not result.solved:
        return None, result, 'No solution from here'
    return result.goal_node.solution(), result, None


class Autoplayer(Entity):
    """Feeds moves into a scene once it is ready for the next one. Any player key takes over.

    on_step(done, total) after each move; on_end(finished) when it stops (finished=False if interrupted).
    """

    GAP = .12      # pause between moves, in seconds

    def __init__(self, scene, moves, on_step=None, on_end=None):
        super().__init__()
        self.scene, self.moves = scene, list(moves)
        self.total, self.done = len(self.moves), 0
        self.on_step, self.on_end = on_step, on_end
        self.wait = .25
        self.running = True

    def update(self):
        if not self.running:
            return
        phase = getattr(self.scene, 'phase', None)
        if phase == 'roll':
            return
        if phase != 'play':                      # won, fell, riding the lift...: the run is over
            self.stop(finished=not self.moves)
            return
        if not self.moves:
            self.stop(finished=True)
            return
        self.wait -= time.dt
        if self.wait > 0:
            return
        self.wait = self.GAP
        action = self.moves.pop(0)
        self.scene.input(ACTION_KEYS[action])
        self.done += 1
        if self.on_step:
            self.on_step(self.done, self.total)

    def input(self, key):
        if self.running and key in PLAYER_KEYS:     # the player took the controls back
            self.stop(finished=False)

    def stop(self, finished=False):
        if not self.running:
            return
        self.running = False
        if self.on_end:
            self.on_end(finished)
        destroy(self)


def ghost(floor, session, state, col=color.rgba(255, 205, 90, 110)):
    """Translucent blocks where ``state`` would put the player; destroy() the returned entity to clear."""
    root = Entity(parent=floor.root)
    cells = session.block_cells(state)
    tall = len(cells) == 1 and not state.split
    for x, y in cells:
        h = 2.0 if tall else 1.0
        Entity(parent=root, model='cube', position=floor.at(x, y, TILE_TOP + h / 2), scale=(.92, h, .92),
               color=col)
    root.setTransparency(True)
    root.setDepthWrite(False)
    root.setLightOff()          # Ursina's cube has no normals: lit, it would come out black
    return root
