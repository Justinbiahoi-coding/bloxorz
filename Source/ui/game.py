import math
import textwrap

import pygame

from engine.problem import DIRS

from . import blockfx, building, rooftop, sprites


MAX_TILE = 112
FALL_MS = 520
WIN_DROP_MS = 420
WIN_LINGER_MS = 900
_TILE_TEXTURE = {'floor': 'concrete', 'goal': 'concrete', 'soft': 'concrete', 'heavy': 'concrete',
                 'split': 'concrete', 'fragile': 'fragile', 'bridge_open': 'steel'}


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
                 show_hint=False, background=None, tile=None, scene=None,
                 free_play=False, has_next=False, tip=None):
        self.surface = surface
        self.W_HEIGHT_SIZE = W_HEIGHT_SIZE
        self.W_WIDTH_SIZE = W_WIDTH_SIZE
        self.CENTER_X = W_WIDTH_SIZE / 2
        self.CENTER_Y = W_HEIGHT_SIZE / 2

        self.session = session
        self.level = session.level

        # drawing: small maps are zoomed in (up to MAX_TILE), the biggest one just fits; board centred
        xs, ys = [x for x, _ in self.level.kinds], [y for _, y in self.level.kinds]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) + 1 + (4 if scene else 0)   # keep two tiles of building in view
        max_tile = int(MAX_TILE * max(1.0, min(2.5, W_HEIGHT_SIZE / 720)))
        self.square_size = tile or min(max_tile, int(min(W_WIDTH_SIZE - 280, W_HEIGHT_SIZE - 140) / span))
        self.starting_x = self.CENTER_X - (min(xs) + max(xs) + 1) / 2 * self.square_size
        self.starting_y = self.CENTER_Y - (min(ys) + max(ys) + 1) / 2 * self.square_size
        self.ending_x = self.starting_x + self.level.size * self.square_size
        self.ending_y = self.starting_y + self.level.size * self.square_size

        # background: sky, plus the skyscraper around the floor in tower mode (scene = (floor, floor_count))
        self.sky = (background or rooftop.sky((W_WIDTH_SIZE, W_HEIGHT_SIZE))).copy()
        self.scene = scene
        self.beacon = building.bake(self.sky, self, *scene) if scene else None

        self.unavailable_color = (10, 10, 10)
        self.available_color = (50, 50, 100)
        self.block_color = (150, 150, 150)
        self.hint_color = (255, 128, 0)
        self.goal_color = (252, 25, 25)
        self._tile_colors = {'floor': self.available_color,
                             'void': self.unavailable_color,
                             'goal': self.goal_color}
        self.line_color = (255, 255, 255)

        self.anim = None         # block roll in progress
        self.block_scale = 1.0   # <1 while the block drops through the goal hole
        self.font = pygame.font.Font(None, 50)
        self.ESC = False
        self.show_hint = show_hint
        self.free_play = free_play
        self.has_next = has_next
        self.tip = tip
        self.result = None
        self.command = None
        self.fall = None
        self.win_pending = False
        self.win_phase = None
        self.win_drop_start = None
        self.win_hold_until = None
        self._result_buttons = []
        self.ui_scale = max(1.0, min(2.5, W_HEIGHT_SIZE / 720))
        self.result_title_font = pygame.font.Font(None, int(58 * self.ui_scale))
        self.result_text_font = pygame.font.Font(None, int(30 * self.ui_scale))
        self.result_button_font = pygame.font.Font(None, int(32 * self.ui_scale))

    def process(self, events):
        if self.result is not None:
            self.process_result_input(events)
        elif self.fall is None and not self.win_pending:
            self.process_input(events)
        self.update_fall()
        self.update_win()
        self.draw()
        if self.result is not None:
            self.draw_result()
        self.process_end()

    def process_input(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if not self.session.won and event.key in _MOVE_KEYS:
                action = _MOVE_KEYS[event.key]
                status, before, after = self.session.attempt_move(action)
                if status == 'fell':
                    if self.free_play:
                        self.start_fall(before, action)
                    continue
                self.start_roll(before, after, action)
                if status == 'won' and self.free_play:
                    self.win_pending = True
                    self.win_phase = 'roll'
                    self.block_scale = 1.0
            elif (self.show_hint and not self.session.won
                  and event.key == pygame.K_h and self.session.hint is None):
                self.session.request_hint()
            elif event.key == pygame.K_ESCAPE:
                self.ESC = True

    def process_result_input(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if (event.key in (pygame.K_n, pygame.K_RETURN, pygame.K_KP_ENTER)
                        and self.result == 'win' and self.has_next):
                    self.command = 'next'
                elif event.key == pygame.K_r:
                    self.command = 'retry'
                elif event.key == pygame.K_ESCAPE:
                    self.command = 'menu'
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, command in self._result_buttons:
                    if rect.collidepoint(event.pos):
                        self.command = command
                        break

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

    def start_fall(self, before, action):
        boxes = self._boxes(before)
        idx = before.active if before.split else 0
        start = boxes[idx]
        self.anim = None
        self.fall = {
            'idx': idx,
            'start': start,
            'end': blockfx.rolled_box(start, DIRS[action]),
            'd': DIRS[action],
            't0': pygame.time.get_ticks(),
        }

    def update_fall(self):
        if self.fall is None:
            return
        if pygame.time.get_ticks() - self.fall['t0'] >= FALL_MS:
            self.fall = None
            if self.free_play:
                self.result = 'lose'

    def update_win(self):
        if not self.win_pending:
            return
        now = pygame.time.get_ticks()
        if self.win_phase == 'roll':
            if self.anim is not None:
                return
            self.win_phase = 'drop'
            self.win_drop_start = now
        if self.win_phase == 'drop':
            p = min(1.0, (now - self.win_drop_start) / WIN_DROP_MS)
            e = p * p * (3 - 2 * p)
            self.block_scale = max(0.0, 1 - e)
            if p >= 1:
                self.win_phase = 'linger'
                self.win_hold_until = now + WIN_LINGER_MS
            return
        if self.win_phase == 'linger' and now >= self.win_hold_until:
            self.win_pending = False
            self.win_phase = None
            self.result = 'win'

    def set_state(self, state, increment_moves=True):
        self.session.set_state(state, increment_moves)

    def process_end(self):
        if self.free_play or not self.session.won:
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
        building.draw_beacon(self.surface, self.beacon, pygame.time.get_ticks())
        self.draw_map()
        self.draw_block()
        self.draw_hint()
        self.draw_tutorial_tip()

    def cell_rect(self, x, y):
        sq = self.square_size
        return pygame.Rect(int(self.starting_x + x * sq), int(self.starting_y + y * sq), int(sq), int(sq))

    def draw_map(self):
        for y in range(self.level.size):
            for x in range(self.level.size):
                kind = self.session.tile_at(x, y)
                if kind != 'void':
                    below = y + 1 >= self.level.size or self.session.tile_at(x, y + 1) in ('void', 'bridge_closed')
                    tex = _TILE_TEXTURE.get(kind)
                    carpet = False
                    if self.scene:                       # path is part of the floor: flush with it
                        below = False
                        carpet = tex == 'concrete' and self.scene[0] > 0   # indoors: a carpet runner
                    piece = sprites.cell_piece(tex, int(self.square_size), x, y) if tex else None
                    if carpet and piece is not None:
                        piece = piece.copy()
                        piece.fill((104, 118, 150), special_flags=pygame.BLEND_RGB_MULT)
                    rect = self.cell_rect(x, y)
                    rooftop.tile(self.surface, rect, kind, below, piece)
                    if self.scene and kind != 'bridge_closed' and not carpet:
                        self.surface.blit(self._path_veil(rect.size), rect.topleft)

    def _path_veil(self, size):
        """Light wash marking the walkable cells without lifting them off the floor."""
        if getattr(self, '_veil', None) is None or self._veil.get_size() != size:
            self._veil = pygame.Surface(size, pygame.SRCALPHA)
            self._veil.fill((255, 244, 220, 34))
        return self._veil

    def draw_block(self):
        if self.result == 'lose':
            return
        boxes, now = self._boxes(self.session.state), pygame.time.get_ticks()
        if self.fall is not None:
            p = min(1.0, (now - self.fall['t0']) / FALL_MS)
            e = p * p * (3 - 2 * p)
            idx = self.fall['idx']
            s, t, d = self.fall['start'], self.fall['end'], self.fall['d']
            box = (s[0] + (t[0] - s[0]) * e, s[1] + (t[1] - s[1]) * e,
                   s[2], s[3], s[4])
            for i in sorted((i for i in range(len(boxes)) if i != idx), key=lambda i: boxes[i][1]):
                blockfx.draw_box(self.surface, boxes[i], (self.starting_x, self.starting_y),
                                 self.square_size, scale=self.block_scale,
                                 ring=self.session.is_split and i == self.session.active)
            blockfx.draw_box(
                self.surface, box,
                (self.starting_x, self.starting_y + e * e * self.square_size * 3),
                self.square_size, (d, e * math.pi / 2), max(0.0, 1 - 0.7 * e))
            return

        roll = None
        if self.anim:
            p = blockfx.progress(self.anim, now)
            if p >= 1:
                self.anim = None
            else:
                boxes[self.anim.idx] = self.anim.box
                roll = (self.anim.d, (p * p * (3 - 2 * p)) * math.pi / 2)
        origin_y = self.starting_y
        if self.free_play and self.win_pending:
            origin_y += (1 - self.block_scale) * self.square_size * 2
        order = sorted(range(len(boxes)), key=lambda i: boxes[i][1])       # northern pieces first
        for i in order:
            blockfx.draw_box(self.surface, boxes[i], (self.starting_x, origin_y), self.square_size,
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

    def draw_tutorial_tip(self):
        if not self.tip or self.result is not None or self.fall is not None or self.win_pending:
            return
        k = self.ui_scale
        max_width = min(int(self.W_WIDTH_SIZE * 0.75), int(1200 * k))
        char_width = max(1, self.result_text_font.size('M')[0])
        lines = textwrap.wrap(self.tip, width=max(24, max_width // char_width))
        images = [self.result_text_font.render(line, True, (250, 244, 232))
                  for line in lines]
        line_height = max(image.get_height() for image in images)
        pad_x, pad_y = int(24 * k), int(14 * k)
        panel = pygame.Rect(0, 0, max(image.get_width() for image in images) + 2 * pad_x,
                            len(images) * line_height + 2 * pad_y)
        panel.midtop = (self.W_WIDTH_SIZE // 2, int(24 * k))
        layer = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (24, 32, 58, 210), layer.get_rect(),
                         border_radius=int(16 * k))
        pygame.draw.rect(layer, (255, 200, 87, 220), layer.get_rect(), 2,
                         border_radius=int(16 * k))
        self.surface.blit(layer, panel.topleft)
        y = panel.y + pad_y
        for image in images:
            self.surface.blit(image, image.get_rect(midtop=(panel.centerx, y)))
            y += line_height

    def draw_result(self):
        k = self.ui_scale
        w, h = self.W_WIDTH_SIZE, self.W_HEIGHT_SIZE
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((8, 12, 28, 170))
        self.surface.blit(shade, (0, 0))

        if self.result == 'win':
            options = []
            if self.has_next:
                options.append(('Next Level', 'next'))
            options.extend((('Retry', 'retry'), ('Main Menu', 'menu')))
        else:
            options = [('Retry', 'retry'), ('Main Menu', 'menu')]

        button_w, button_h, gap = int(340 * k), int(54 * k), int(14 * k)
        start_y = int(140 * k)
        panel_w = int(540 * k)
        panel_h = start_y + len(options) * (button_h + gap) + int(70 * k)
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (w // 2, h // 2)
        pygame.draw.rect(self.surface, (24, 32, 58), panel, border_radius=int(22 * k))
        pygame.draw.rect(self.surface, (255, 200, 87), panel, 2, border_radius=int(22 * k))

        if self.result == 'win':
            title = 'ALL LEVELS CLEARED' if not self.has_next else 'LEVEL CLEARED'
            color = (255, 200, 87)
        else:
            title = 'YOU FELL'
            color = (255, 138, 91)
        image = self.result_title_font.render(title, True, color)
        self.surface.blit(image, image.get_rect(center=(panel.centerx, panel.y + int(50 * k))))
        subtitle = 'Level {}  -  {} moves'.format(self.session.level_number, self.session.moves)
        image = self.result_text_font.render(subtitle, True, (230, 226, 216))
        self.surface.blit(image, image.get_rect(center=(panel.centerx, panel.y + int(100 * k))))

        self._result_buttons = []
        mouse = pygame.mouse.get_pos()
        y = panel.y + start_y
        for label, command in options:
            rect = pygame.Rect(0, 0, button_w, button_h)
            rect.center = (panel.centerx, y + button_h // 2)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(self.surface, (255, 200, 87) if hover else (44, 58, 94),
                             rect, border_radius=int(12 * k))
            image = self.result_button_font.render(
                label, True, (27, 37, 64) if hover else (250, 244, 232))
            self.surface.blit(image, image.get_rect(center=rect.center))
            self._result_buttons.append((rect, command))
            y += button_h + gap

        if self.result == 'win' and self.has_next:
            hint = 'N next    R retry    Esc menu'
        else:
            hint = 'R retry    Esc menu'
        image = self.result_text_font.render(hint, True, (190, 196, 216))
        self.surface.blit(image, image.get_rect(center=(panel.centerx, panel.bottom - int(32 * k))))

    def should_quit(self):
        return self.ESC
