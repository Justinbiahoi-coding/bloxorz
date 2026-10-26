import unittest
from dataclasses import dataclass
from unittest.mock import patch

from engine import GameSession, solve, solve_problem
from engine.algo_implementation.algorithms import uniform_cost_search
from engine.algo_implementation.node import Node
from engine.algo_implementation.problem import Problem


class WeightedGraphProblem(Problem):
    """Edges map each action to (next_state, step_cost)."""

    def __init__(self, graph, initial='S', goal='G'):
        super().__init__(initial, goal)
        self.graph = graph
        self.expanded_states = []
        self.goal_checks = []

    def actions(self, state):
        self.expanded_states.append(state)
        return list(self.graph.get(state, {}))

    def result(self, state, action):
        return self.graph[state][action][0]

    def path_cost(self, cost, state1, action, state2):
        return cost + self.graph[state1][action][1]

    def goal_test(self, state):
        self.goal_checks.append(state)
        return super().goal_test(state)


@dataclass(frozen=True)
class GraphState:
    position: tuple
    mode: str


class UCSTests(unittest.TestCase):
    def assert_expanded(self, problem, nodes, expected):
        self.assertTrue(all(isinstance(node, Node) for node in nodes))
        self.assertEqual([node.state for node in nodes], expected)
        self.assertEqual(problem.expanded_states, expected)

    def test_initial_state_is_goal(self):
        problem = WeightedGraphProblem({}, initial='G')

        goal, explored, elapsed_ms = uniform_cost_search(problem)

        self.assertIsInstance(goal, Node)
        self.assertEqual(goal.state, 'G')
        self.assertIsNone(goal.parent)
        self.assertEqual(goal.solution(), [])
        self.assertEqual(goal.path_cost, 0)
        self.assertEqual(goal.depth, 0)
        self.assert_expanded(problem, explored, [])
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_no_solution(self):
        problem = WeightedGraphProblem({'S': {'next': ('A', 4)}})

        goal, explored, elapsed_ms = uniform_cost_search(problem)

        self.assertIsNone(goal)
        self.assert_expanded(problem, explored, ['S', 'A'])
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_cycles_do_not_repeat_expansion(self):
        problem = WeightedGraphProblem({
            'S': {'stay': ('S', 1), 'to_a': ('A', 1)},
            'A': {'back': ('S', 1), 'to_b': ('B', 1)},
            'B': {'back': ('A', 1)},
        })

        goal, explored, _ = uniform_cost_search(problem)

        self.assertIsNone(goal)
        self.assert_expanded(problem, explored, ['S', 'A', 'B'])

    def test_lower_cost_wins_over_fewer_actions(self):
        problem = WeightedGraphProblem({
            'S': {'short_branch': ('A', 1), 'long_branch': ('B', 1)},
            'A': {'expensive_finish': ('G', 9)},
            'B': {'to_c': ('C', 1)},
            'C': {'cheap_finish': ('G', 1)},
        })

        goal, explored, _ = uniform_cost_search(problem)

        self.assertEqual(goal.solution(), ['long_branch', 'to_c', 'cheap_finish'])
        self.assertEqual(goal.path_cost, 3)
        self.assertEqual(goal.depth, 3)
        self.assert_expanded(problem, explored, ['S', 'A', 'B', 'C'])

    def test_cheaper_path_replaces_old_entry_and_stale_entry_is_skipped(self):
        problem = WeightedGraphProblem({
            'S': {'expensive_a': ('A', 10), 'to_b': ('B', 1)},
            'B': {'cheap_a': ('A', 1)},
            'A': {'finish': ('G', 20)},
        })

        goal, explored, _ = uniform_cost_search(problem)

        self.assertEqual(goal.solution(), ['to_b', 'cheap_a', 'finish'])
        self.assertEqual(goal.path_cost, 22)
        self.assertEqual([node.state for node in goal.path()], ['S', 'B', 'A', 'G'])
        self.assert_expanded(problem, explored, ['S', 'B', 'A'])
        # The obsolete A(cost=10) is popped before G(cost=22), but never checked
        # as a goal or expanded. The valid A was expanded with cost=2.
        self.assertEqual(problem.goal_checks, ['S', 'B', 'A', 'G'])
        self.assertEqual([node.path_cost for node in explored], [0, 1, 2])

    def test_expensive_goal_generated_first_is_not_accepted_early(self):
        problem = WeightedGraphProblem({
            'S': {'expensive_goal': ('G', 10), 'to_a': ('A', 1)},
            'A': {'cheap_goal': ('G', 1)},
        })

        goal, explored, _ = uniform_cost_search(problem)

        self.assertEqual(goal.solution(), ['to_a', 'cheap_goal'])
        self.assertEqual(goal.path_cost, 2)
        self.assert_expanded(problem, explored, ['S', 'A'])

    def test_equal_costs_do_not_require_orderable_states(self):
        start = GraphState((0, 0), 'start')
        first = GraphState((1, 0), 'first')
        second = GraphState((2, 0), 'second')
        target = GraphState((3, 0), 'goal')
        problem = WeightedGraphProblem({
            start: {'first': (first, 1), 'second': (second, 1)},
            first: {'finish': (target, 1)},
            second: {'finish': (target, 1)},
        }, start, target)

        goal, explored, _ = uniform_cost_search(problem)

        self.assertEqual(goal.solution(), ['first', 'finish'])
        self.assertEqual(goal.path_cost, 2)
        self.assert_expanded(problem, explored, [start, first, second])

    def test_zero_cost_cycles_and_ties_terminate_with_zero_cost_solution(self):
        problem = WeightedGraphProblem({
            'S': {'to_b': ('B', 0), 'to_a': ('A', 0)},
            'B': {'stay': ('B', 0), 'back': ('S', 0), 'finish': ('G', 0)},
            'A': {'back': ('S', 0), 'to_b': ('B', 0), 'finish': ('G', 0)},
        })

        goal, explored, _ = uniform_cost_search(problem)

        self.assertEqual(goal.solution(), ['to_b', 'finish'])
        self.assertEqual(goal.path_cost, 0)
        self.assert_expanded(problem, explored, ['S', 'B', 'A'])

    def test_best_cost_uses_whole_state_without_mutation(self):
        initial = GraphState((0, 0), 'initial')
        changed = GraphState((0, 0), 'changed')
        target = GraphState((1, 0), 'changed')
        problem = WeightedGraphProblem({
            initial: {'change_mode': (changed, 0)},
            changed: {'finish': (target, 2)},
        }, initial, target)

        goal, explored, _ = uniform_cost_search(problem)

        self.assertEqual(goal.state, target)
        self.assertEqual(goal.path_cost, 2)
        self.assertEqual(initial, GraphState((0, 0), 'initial'))
        self.assert_expanded(problem, explored, [initial, changed])

    def test_elapsed_time_is_in_milliseconds_for_every_outcome(self):
        cases = [
            ('initial_goal', WeightedGraphProblem({}, initial='G')),
            ('found_goal', WeightedGraphProblem({'S': {'finish': ('G', 1)}})),
            ('no_solution', WeightedGraphProblem({})),
        ]
        for name, problem in cases:
            with self.subTest(outcome=name):
                with patch(
                    'engine.algo_implementation.algorithms.time.perf_counter',
                    side_effect=[10.0, 10.125],
                ) as timer:
                    result = uniform_cost_search(problem)
                self.assertIsInstance(result, list)
                self.assertEqual(len(result), 3)
                self.assertEqual(result[2], 125.0)
                self.assertEqual(timer.call_count, 2)

    def test_level_one_solution_replays_to_goal(self):
        result = solve(1, 'Uniform Cost Search')
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
        self.assertNotIn(result.goal_node.state, [node.state for node in result.explored])

    def test_search_can_start_from_current_session_state(self):
        session = GameSession(1)
        original_initial = session.problem.initial
        self.assertTrue(session.move('RIGHT'))
        current_state = session.state
        before = (list(current_state.position), current_state.bridges,
                  current_state.split, current_state.active)

        result = solve_problem(session.problem, 'Uniform Cost Search', initial=current_state)

        self.assertTrue(result.solved)
        self.assertIs(result.solution_path()[0].state, current_state)
        self.assertIs(session.problem.initial, original_initial)
        self.assertEqual((current_state.position, current_state.bridges,
                          current_state.split, current_state.active), before)
        for action in result.goal_node.solution():
            self.assertTrue(session.move(action), action)
        self.assertTrue(session.won)


if __name__ == '__main__':
    unittest.main()
