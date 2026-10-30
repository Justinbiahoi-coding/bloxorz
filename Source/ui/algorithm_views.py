import pygame
from engine import GameSession, count_moves, solve
from .game import Game

class AlgorithmMenu():
        def __init__(self, surface, W_HEIGHT_SIZE, W_WIDTH_SIZE, level_number, algorithm):
            self.surface = surface
            self.W_HEIGHT_SIZE = W_HEIGHT_SIZE
            self.W_WIDTH_SIZE = W_WIDTH_SIZE
            self.CENTER_X = W_WIDTH_SIZE / 2
            self.CENTER_Y = W_HEIGHT_SIZE / 2
            self.big_font = pygame.font.Font(None, 50)
            self.medium_font = pygame.font.Font(None, 42)
            self.small_font = pygame.font.Font(None, 35)
            self.algorithm = algorithm
            self.level_number = level_number
            self.ESC = False
            self.S = False
            self.N = False
            # Solve Problem
            self.run_algorithm(level_number)
            

        def run_algorithm(self, level_number):
            self.result = solve(level_number, self.algorithm)
            self.goal_node = self.result.goal_node
            self.explored_ordered = self.result.explored
            self.timeMS = self.result.elapsed_ms
            self.solution_cost = self.result.solution_cost

        def process(self, events):
            self.process_input(events)
            self.draw()

        def process_input(self, events):
            for event in events:
                if (event.type == pygame.KEYDOWN):
                    if not hasattr(event, 'key'):
                        continue
                    if event.key == pygame.K_ESCAPE:
                        self.ESC = True # Exit game
                    elif event.key == pygame.K_s:
                        if self.solution_cost is not None:
                            self.S = True
                    elif event.key == pygame.K_n:
                        if self.solution_cost is not None:
                            self.N = True
                    elif event.key == pygame.K_r:
                        self.run_algorithm(self.level_number)
                    elif event.key == pygame.K_a:
                        print("### Algorithm {}".format(self.algorithm))
                        """
                            Python optimizes the code during run time. The first loop exists because when we were testing we noticed
                            that the first maps had a really high solve time in comparison to the last ones. Our solution isn't pretty,
                            but hey, it works.
                        """ 
                        for x in range(1, self.level_number + 1):
                            self.run_algorithm(x) 
                        for x in range(1, self.level_number + 1):
                            print("# Map {}".format(x))
                            self.run_algorithm(x)
                            if self.goal_node is not None:
                                print("Solution Cost: {}".format(self.solution_cost))
                                print("Nodes explored: {}".format(len(self.explored_ordered)))
                                time_solved_ms = self.timeMS
                                for i in range(4):
                                    self.run_algorithm(x)
                                    time_solved_ms += self.timeMS
                                print("Solved in: {0:.3f}ms (avg 5 times)".format(time_solved_ms / 5))
                            else:
                                print("Could not find solution.")
                                print("Nodes explored: {}".format(len(self.explored_ordered)))
                                time_solved_ms = self.timeMS
                                for i in range(4):
                                    self.run_algorithm(x)
                                    time_solved_ms += self.timeMS
                                print("Completed in: {0:.3f}ms (avg 5 times)".format(time_solved_ms / 5))
                        self.ESC = True

        
        def should_quit(self):
            return self.ESC
        
        def show_solution(self):
            if self.S:
                return self.result.solution_path()
            return None
        
        def show_explored_nodes(self):
            if self.N:
                return self.explored_ordered
            return None

        def draw(self):
            # Algorithm header
            text = self.big_font.render("Algorithm: {}".format(self.algorithm), True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 50))
            self.surface.blit(text, text_rect)
            # Map header
            text = self.big_font.render("Map: {}".format(self.level_number), True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 95))
            self.surface.blit(text, text_rect)
            if self.solution_cost is not None:
                # Solution Cost
                text = self.medium_font.render("Solution Cost: {}".format(self.solution_cost), True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 250))
                self.surface.blit(text, text_rect)
            # Nodes Explored
            text = self.medium_font.render("Nodes explored: {}".format(len(self.explored_ordered)), True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 300))
            self.surface.blit(text, text_rect)
            if self.solution_cost is not None:
                # Time to Solve
                text = self.medium_font.render("Solved in: {0:.3f}ms".format(self.timeMS), True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 350))
                self.surface.blit(text, text_rect)
                # Press S to VIEW SOLUTION.
                text = self.small_font.render("Press S to view solution steps.", True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, self.W_HEIGHT_SIZE - 166))
                self.surface.blit(text, text_rect)
                # Press N to VIEW NODES EXPLORED.
                text = self.small_font.render("Press N to view nodes explored.", True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, self.W_HEIGHT_SIZE - 128))
                self.surface.blit(text, text_rect)
            else:
                # Time to Solve
                text = self.medium_font.render("Gave up after: {0:.3f}ms".format(self.timeMS), True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 350))
                self.surface.blit(text, text_rect)
                # NO SOLUTION FOUND
                text = self.small_font.render("NO SOLUTION FOUND.", True, (255, 255, 255))
                text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, self.W_HEIGHT_SIZE - 200))
                self.surface.blit(text, text_rect)
            # Press R to re run algorithm.
            text = self.small_font.render("Press R to run the algorithm again.", True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, self.W_HEIGHT_SIZE - 90))
            self.surface.blit(text, text_rect)
            # Press ESC to go back.
            text = self.small_font.render("Press ESC to go back.", True, (255, 255, 255))
            text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, self.W_HEIGHT_SIZE - 35))
            self.surface.blit(text, text_rect)

   
class AlgorithmShow():
    def __init__(self, surface, W_HEIGHT_SIZE, W_WIDTH_SIZE, level_number, solution, header_text, transition_speed_ms, show_win_moves = True):
            self.surface = surface
            self.W_HEIGHT_SIZE = W_HEIGHT_SIZE
            self.W_WIDTH_SIZE = W_WIDTH_SIZE
            self.CENTER_X = W_WIDTH_SIZE / 2
            self.CENTER_Y = W_HEIGHT_SIZE / 2
            font_size = 2200 // len(header_text)
            self.font = pygame.font.Font(None, font_size)
            self.ESC = False
            self.game = Game(surface, W_HEIGHT_SIZE, W_WIDTH_SIZE, GameSession(level_number))
            self.header_text = header_text
            self.solution = solution  
            self.time_since_start = 0
            self.transition_speed_ms = transition_speed_ms
            self.show_win_moves = show_win_moves

    def process(self, events, deltatime):
        self.draw_header()
        #
        self.game.set_state(self.get_manipulated_state(deltatime), 0)
        self.game.draw()
        self.game.process_end()
        #
        self.process_input(events)

    def process_input(self, events):
        for event in events:
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.ESC = True

    def draw_header(self):
        text = self.font.render(self.header_text, True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.W_WIDTH_SIZE/2, 40))
        self.surface.blit(text, text_rect)

    def should_quit(self):
        return self.ESC
        
    def get_manipulated_state(self, deltatime):
        self.time_since_start += deltatime  
        state_index = self.time_since_start // self.transition_speed_ms
        if state_index >= len(self.solution):
            state_index = len(self.solution) - 1
        if self.show_win_moves:
            # Prefix length follows every replay action; MOVES excludes SWITCH.
            self.game.session.moves = count_moves(
                getattr(node, 'action', None) for node in self.solution[1:state_index + 1])
        if hasattr(self.solution[state_index], 'state'):
           state = self.solution[state_index].state
        else:
           state = self.solution[state_index]
        return state
