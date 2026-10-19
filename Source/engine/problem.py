from .algo_implementation.problem import Problem
from .level import Level


class Bloxorz(Problem):

    def __init__(self, map_number):
        self.level = Level(map_number)
        initial = State(self.level.start)
        goal = State(self.level.end)
        Problem.__init__(self, initial, goal)
        
    def new_possible_states(self, state):
        possible_actions = self.actions(state)
        possible_states = []
        for action in possible_actions:
            possible_states.insert(len(possible_states), self.result(state, action))
        return possible_states
    
    def actions(self, state):
        possible_actions = []

        # Vertical Position
        if len(state.position) == 2:
            x = state.position[0]
            y = state.position[1]
            # UP
            if self.level.is_tile_available(x, y + 1) and self.level.is_tile_available(x, y + 2):
                possible_actions.append('UP')
            # DOWN
            if self.level.is_tile_available(x, y - 1) and self.level.is_tile_available(x, y - 2):
                possible_actions.append('DOWN')
            # LEFT
            if self.level.is_tile_available(x - 1, y) and self.level.is_tile_available(x - 2, y):
                possible_actions.append('LEFT')
            # RIGHT
            if self.level.is_tile_available(x + 1, y) and self.level.is_tile_available(x + 2, y):
                possible_actions.append('RIGHT')
        # Horizontal Position
        else:
            x1 = state.position[0]
            y1 = state.position[1]
            x2 = state.position[2]
            y2 = state.position[3]
            # Horizontal on row.
            if x1 == x2:
                # DOWN
                if self.level.is_tile_available(x2, y2 - 1):
                    possible_actions.append('DOWN')
                # UP
                if self.level.is_tile_available(x1, y1 + 1):
                    possible_actions.append('UP')
                # LEFT
                if self.level.is_tile_available(x1 - 1, y1) and self.level.is_tile_available(x2 - 1, y2):
                    possible_actions.append('LEFT')
                # RIGHT
                if self.level.is_tile_available(x1 + 1, y1) and self.level.is_tile_available(x2 + 1, y2):
                    possible_actions.append('RIGHT')
            # Horizontal on column.
            else:
                # DOWN
                if self.level.is_tile_available(x1, y1 - 1) and self.level.is_tile_available(x2, y2 - 1):
                    possible_actions.append('DOWN')
                # UP
                if self.level.is_tile_available(x1, y1 + 1) and self.level.is_tile_available(x2, y2 + 1):
                    possible_actions.append('UP')
                # LEFT
                if self.level.is_tile_available(x1 - 1, y1):
                    possible_actions.append('LEFT')
                # RIGHT
                if self.level.is_tile_available(x2 + 1, y2):
                    possible_actions.append('RIGHT')  

        return possible_actions

    def result(self, state, action):

        new_state = []
        
        # Vertical Position
        if len(state.position) == 2:
            x = state.position[0]
            y = state.position[1]
            # UP
            if action == 'UP':
                new_state = [x, y+2, x, y+1]
            # DOWN
            elif action == 'DOWN':
                new_state = [x, y-1, x, y-2]
            # LEFT
            elif action == 'LEFT':
                new_state = [x-2, y, x-1, y]
            # RIGHT
            elif action == 'RIGHT':
                new_state = [x+1, y, x+2, y]
        # Horizontal Position
        else:
            x1 = state.position[0]
            y1 = state.position[1]
            x2 = state.position[2]
            y2 = state.position[3]
            # Horizontal on row.
            if x1 == x2:
                # UP
                if action == 'UP':
                    new_state = [x1, y1+1]
                # DOWN
                elif action == 'DOWN':
                    new_state = [x2, y2-1]
                # LEFT
                elif action == 'LEFT':
                    new_state = [x1-1, y1, x2-1, y2]
                # RIGHT
                elif action == 'RIGHT':
                    new_state = [x1+1, y1, x2+1, y2]
            # Horizontal on column.
            else:
                # UP
                if action == 'UP':
                    new_state = [x1, y1+1, x2, y2+1]
                # DOWN
                elif action == 'DOWN':
                    new_state = [x1, y1-1, x2, y2-1]
                # LEFT
                elif action == 'LEFT':
                    new_state = [x1-1, y1]
                # RIGHT
                elif action == 'RIGHT':
                    new_state = [x2+1, y2]
        

        return State(new_state)
    
    def do_action_if_possible(self, state, action):
        if action in self.actions(state):
            return self.result(state, action)
        return None

    ## Manhattan distance based heuristic.
    def h1(self, node):
        [x_goal, y_goal] = self.goal.position

        if len(node.state.position) == 2:
            [x_block, y_block] = node.state.position
        else: 
            # Select position of the block nearest to the goal.
            [block_pos_x1, block_pos_y1, block_pos_x2, block_pos_y2] = node.state.position
            [x_block, y_block] = self.closest_point(x_goal, y_goal, block_pos_x1, block_pos_y1, block_pos_x2, block_pos_y2)

        return (abs(x_goal - x_block) + abs(y_goal - y_block)) // 2

    # Returns the closest point to the goal based on the manhattam distance
    def closest_point(self, x_goal, y_goal, x1, y1, x2, y2):
        distance_1 = abs(x_goal - x1) + abs(y_goal - y1)
        distance_2 = abs(x_goal - x2) + abs(y_goal - y2)
        if distance_1 > distance_2:
            return [x2, y2]
        else:
            return [x1, y1]

# Custom state for Bloxorz
class State():
    def __init__(self, position):
        self.position = position

    def __hash__(self):
        return hash(str(self.position))

    def __eq__(self, other):
        return isinstance(other, State) and self.position == other.position
         
    def __lt__(self, node):
        return self.position < node.position