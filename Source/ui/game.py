import math

import pygame

from engine.problem import DIRS

from . import blockfx, rooftop


MAX_TILE = 112


# Keyboard key -> engine action.
_MOVE_KEYS = {
    pygame.K_LEFT: 'LEFT',
    pygame.K_RIGHT: 'RIGHT',
    pygame.K_UP: 'DOWN',
    pygame.K_DOWN: 'UP',
    pygame.K_SPACE: 'SWITCH',   # change the active cube when the block is split
}


class Game:
    """Pygame view/controller for an engine GameSession."""

    def __init__(self, surface, W_HEIGHT_SIZE, W_WIDTH_SIZE, session,
                 show_hint=False, background=None, tile=None):
        self.surface = surface
        self.W_HEIGHT_SIZE = W_HEIGHT_SIZE
        self.W_WIDTH_SIZE = W_WIDTH_SIZE
        self.CENTER_X = W_WIDTH_SIZE / 2
        self.CENTER_Y = W_HEIGHT_SIZE / 2

        self.session = session
        self.level = session.level

        # drawing: small maps are zoomed in (up to MAX_TILE), the biggest one just fits; board centred
        xs, ys = [x for x, _ in self.level.kinds], [y for _, y in self.level.kinds]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) + 1
        self.square_size = tile or min(MAX_TILE, int(min(W_WIDTH_SIZE - 280, W_HEIGHT_SIZE - 140) / span))
        self.starting_x = self.CENTER_X - (min(xs) + max(xs) + 1) / 2 * self.square_size
        self.starting_y = self.CENTER_Y - (min(ys) + max(ys) + 1) / 2 * self.square_size
        self.ending_x = self.starting_x + self.level.size * self.square_size
        self.ending_y = self.starting_y + self.level.size * self.square_size

        self.unavailable_color = (10, 10, 10)
        self.available_color = (50, 50, 100)
        self.block_color = (150, 150, 150)
        self.hint_color = (255, 128, 0)
        self.goal_color = (252, 25, 25)
        self._tile_colors = {'floor': self.available_color,
                             'void': self.unavailable_color,
                             'goal': self.goal_color}
        self.line_color = (255, 255, 255)

        self.sky = background or rooftop.sky((W_WIDTH_SIZE, W_HEIGHT_SIZE))
        self.anim = None         # block roll in progress
        self.block_scale = 1.0   # <1 while the block drops through the goal hole
        self.font = pygame.font.Font(None, 50)
        self.ESC = False
        self.show_hint = show_hint

    def process(self, events):
        self.process_input(events)
        self.draw()
        self.process_end()

    def process_input(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if not self.session.won and event.key in _MOVE_KEYS:
                before, action = self.session.state, _MOVE_KEYS[event.key]
                if self.session.move(action):
                    self.start_roll(before, self.session.state, action)
            elif (not self.session.won and event.key == pygame.K_h
                  and self.session.hint is None):
                self.session.request_hint()
            elif event.key == pygame.K_ESCAPE:
                self.ESC = True

    def _boxes(self, state):
        cells = self.session.block_cells(state)
        if state.split:
            return [blockfx.make_box([c], True) for c in cells]
        return [blockfx.make_box(cells, False)]

    def start_roll(self, before, after, action):
        """Animate the move unless it is not a plain roll (switching cube, splitting, merging)."""
        self.anim = None
        if action == 'SWITCH' or before.split != after.split:
            return
        idx = before.active if before.split else 0
        start, end = self._boxes(before)[idx], self._boxes(after)[idx]
        if blockfx.rolls_to(start, DIRS[action], end):
            self.anim = blockfx.start_roll(start, DIRS[action], idx, pygame.time.get_ticks())

    def set_state(self, state, increment_moves=True):
        self.session.set_state(state, increment_moves)

    def process_end(self):
        if not self.session.won:
            return

        if self.session.moves > 0:
            text = self.font.render(
                "Win at {} moves. Press ESC to go back.".format(
                    self.session.moves), True, (255, 255, 255))
        else:
            text = self.font.render(
                "Press ESC to go back.", True, (255, 255, 255))
        text_rect = text.get_rect(
            center=(self.W_WIDTH_SIZE / 2, self.W_HEIGHT_SIZE - 35))
        self.surface.blit(text, text_rect)

    def draw(self):
        self.surface.blit(self.sky, (0, 0))
        self.draw_map()
        self.draw_block()
        self.draw_hint()

    def cell_rect(self, x, y):
        sq = self.square_size
        return pygame.Rect(int(self.starting_x + x * sq), int(self.starting_y + y * sq), int(sq), int(sq))

    def draw_map(self):
        for y in range(self.level.size):
            for x in range(self.level.size):
                kind = self.session.tile_at(x, y)
                if kind != 'void':
                    below = y + 1 >= self.level.size or self.session.tile_at(x, y + 1) in ('void', 'bridge_closed')
                    rooftop.tile(self.surface, self.cell_rect(x, y), kind, below)

    def draw_block(self):
        boxes, roll, now = self._boxes(self.session.state), None, pygame.time.get_ticks()
        if self.anim:
            p = blockfx.progress(self.anim, now)
            if p >= 1:
                self.anim = None
            else:
                boxes[self.anim.idx] = self.anim.box
                roll = (self.anim.d, (p * p * (3 - 2 * p)) * math.pi / 2)
        order = sorted(range(len(boxes)), key=lambda i: boxes[i][1])       # northern pieces first
        for i in order:
            blockfx.draw_box(self.surface, boxes[i], (self.starting_x, self.starting_y), self.square_size,
                             roll if self.anim and i == self.anim.idx else None, self.block_scale,
                             ring=self.session.is_split and i == self.session.active)

    def draw_map_square(self, x, y, color):
        rect = pygame.Rect(
            int(self.starting_x + 1 + x * self.square_size),
            int(self.starting_y + 1 + y * self.square_size),
            int(self.square_size - 1),
            int(self.square_size - 1),
        )
        pygame.draw.rect(self.surface, color, rect)

    def draw_cells(self, cells, color):
        for x, y in cells:
            self.draw_map_square(x, y, color)
        if len(cells) == 2 and abs(cells[0][0] - cells[1][0]) + abs(cells[0][1] - cells[1][1]) == 1:  # fill the gap between the two halves
            (x1, y1), (x2, y2) = cells
            self.draw_map_square((x1 + x2) / 2, (y1 + y2) / 2, color)

    def draw_hint(self):
        if not self.show_hint:
            return

        if self.session.hint is not None:
            self.draw_cells(self.session.block_cells(self.session.hint.state),
                            self.hint_color)
        elif not self.session.won:
            text = self.font.render(
                "Feeling Trapped? Press H for a hint.",
                True, (255, 255, 255))
            text_rect = text.get_rect(
                center=(self.W_WIDTH_SIZE / 2, self.W_HEIGHT_SIZE - 35))
            self.surface.blit(text, text_rect)

    def should_quit(self):
        return self.ESC
