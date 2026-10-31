import unittest
from dataclasses import dataclass
from unittest.mock import patch

from engine import GameSession, solve, solve_problem
from engine.algo_implementation.algorithms import breadth_first_graph_search
from engine.algo_implementation.node import Node
from engine.algo_implementation.problem import Problem


class GraphProblem(Problem):
    """Small deterministic graphs with known paths, independent of game rules."""

    def __init__(self, graph, initial, goal):
        super().__init__(initial, goal)
        self.graph = graph
        self.expanded_states = []

    def actions(self, state):
        self.expanded_states.append(state)
        return list(self.graph.get(state, {}))

    def result(self, state, action):
        return self.graph[state][action]


@dataclass(frozen=True)
class GraphState:
    position: tuple
    mode: str


class BFSTests(unittest.TestCase):
    def test_initial_state_is_goal(self):
        problem = GraphProblem({}, 'G', 'G')

        goal, explored, elapsed_ms = breadth_first_graph_search(problem)

        self.assertIsInstance(goal, Node)
        self.assertEqual(goal.state, problem.initial)
        self.assertIsNone(goal.parent)
        self.assertEqual(goal.depth, 0)
        self.assertEqual(goal.path_cost, 0)
        self.assertEqual(goal.solution(), [])
        self.assertEqual(explored, [goal])
        self.assertEqual(problem.expanded_states, [])
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_no_solution(self):
        problem = GraphProblem({'S': {'next': 'A'}}, 'S', 'G')

        goal, explored, elapsed_ms = breadth_first_graph_search(problem)

        self.assertIsNone(goal)
        self.assertTrue(all(isinstance(node, Node) for node in explored))
        self.assertEqual([node.state for node in explored], ['S', 'A'])
        self.assertEqual(problem.expanded_states, ['S', 'A'])
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_cycles_and_multiple_paths_expand_each_state_once(self):
        problem = GraphProblem({
            'S': {'stay': 'S', 'to_a': 'A', 'to_b': 'B'},
            'A': {'back': 'S', 'to_c': 'C'},
            'B': {'to_c': 'C'},
            'C': {'back': 'A'},
        }, 'S', 'G')

        goal, explored, _ = breadth_first_graph_search(problem)

        self.assertIsNone(goal)
        states = [node.state for node in explored]
        self.assertEqual(states, ['S', 'A', 'B', 'C'])
        self.assertEqual(len(states), len(set(states)))
        self.assertEqual(problem.expanded_states, states)

    def test_shortest_path_records_goal_but_does_not_generate_its_children(self):
        problem = GraphProblem({
            'S': {'long_branch': 'A', 'short_branch': 'B'},
            'A': {'to_c': 'C'},
            'C': {'long_finish': 'G'},
            'B': {'short_finish': 'G'},
        }, 'S', 'G')

        goal, explored, _ = breadth_first_graph_search(problem)

        self.assertEqual(goal.solution(), ['short_branch', 'short_finish'])
        self.assertEqual([node.state for node in goal.path()], ['S', 'B', 'G'])
        self.assertEqual(goal.depth, 2)
        self.assertEqual(goal.path_cost, 2)
        self.assertEqual([node.state for node in explored], ['S', 'A', 'B', 'C', 'G'])
        self.assertEqual(problem.expanded_states, ['S', 'A', 'B', 'C'])

    def test_discovery_uses_whole_state(self):
        initial = GraphState((0, 0), 'initial')
        changed = GraphState((0, 0), 'changed')
        target = GraphState((1, 0), 'changed')
        problem = GraphProblem({
            initial: {'change_mode': changed},
            changed: {'finish': target},
        }, initial, target)

        goal, explored, _ = breadth_first_graph_search(problem)

        self.assertEqual(goal.state, target)
        self.assertEqual(goal.solution(), ['change_mode', 'finish'])
        self.assertEqual([node.state for node in explored], [initial, changed, target])

    def test_elapsed_time_is_in_milliseconds_for_every_outcome(self):
        cases = [
            ('initial_goal', GraphProblem({}, 'G', 'G')),
            ('found_goal', GraphProblem({'S': {'finish': 'G'}}, 'S', 'G')),
            ('no_solution', GraphProblem({}, 'S', 'G')),
        ]
        for name, problem in cases:
            with self.subTest(outcome=name):
                with patch(
                    'engine.algo_implementation.algorithms.time.perf_counter',
                    side_effect=[10.0, 10.125],
                ) as timer:
                    result = breadth_first_graph_search(problem)
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 3)
                self.assertEqual(result[2], 125.0)
                self.assertEqual(timer.call_count, 2)

    def test_level_one_solution_replays_to_goal(self):
        result = solve(1, 'BFS')
        session = GameSession(1)

        self.assertTrue(result.solved)
        self.assertGreaterEqual(result.elapsed_ms, 0)
        actions = result.goal_node.solution()
        for action in actions:
            self.assertTrue(session.move(action), action)

        self.assertTrue(session.won)
        self.assertEqual(session.moves, len(actions))
        self.assertEqual(result.goal_node.depth, len(actions))
        self.assertEqual(result.solution_cost, len(actions))
        self.assertEqual(result.solution_path()[0].state, session.problem.initial)
        self.assertEqual(result.explored[-1], result.goal_node)
        self.assertEqual([node.state for node in result.explored].count(result.goal_node.state), 1)
        self.assertEqual(len(result.explored), len({node.state for node in result.explored}))

    def test_bfs_can_start_from_current_session_state(self):
        session = GameSession(1)
        original_initial = session.problem.initial
        self.assertTrue(session.move('RIGHT'))
        current_state = session.state
        initial_position = list(original_initial.position)
        current_position = list(current_state.position)

        result = solve_problem(session.problem, 'BFS', initial=current_state)

        self.assertTrue(result.solved)
        self.assertIs(result.solution_path()[0].state, current_state)
        self.assertIs(session.problem.initial, original_initial)
        self.assertEqual(original_initial.position, initial_position)
        self.assertEqual(current_state.position, current_position)
        for action in result.goal_node.solution():
            self.assertTrue(session.move(action), action)
        self.assertTrue(session.won)


if __name__ == '__main__':
    unittest.main()
