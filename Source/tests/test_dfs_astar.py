"""Tests for DFS and A* search algorithms.

Covers:
- Solvable levels (level 1 and small levels 2-4)
- Solution replay through the actual transition model
- A* optimality verification
- Unsolvable problems
- Initial-state-is-goal edge case
- Cycle handling with visited-set detection
"""
import unittest

from engine import solve
from engine.problem import Bloxorz, State
from engine.algo_implementation.problem import Problem
from engine.algo_implementation.algorithms import (
    depth_first_graph_search,
    astar_search,
)


# ────────────────────────── DFS tests ──────────────────────────────

class TestDFS(unittest.TestCase):
    """DFS: solvability, replay, cycles, unsolvable, edge cases."""

    def test_solves_level_one(self):
        result = solve(1, 'DFS')
        self.assertTrue(result.solved)
        self.assertIsNotNone(result.solution_path())
        self.assertGreater(len(result.explored), 0)
        self.assertGreaterEqual(result.elapsed_ms, 0)

    def test_solution_replays_to_goal(self):
        """Every returned action is legal; the final state passes goal_test."""
        problem = Bloxorz(1)
        goal_node, _, _ = depth_first_graph_search(problem)
        self.assertIsNotNone(goal_node)

        state = problem.initial
        for action in goal_node.solution():
            self.assertIn(action, problem.actions(state),
                          f"Action {action} not legal in state {state.position}")
            state = problem.result(state, action)

        self.assertTrue(problem.goal_test(state),
                        f"Final state {state.position} is not the goal")

    def test_handles_cycle(self):
        """DFS must terminate on a cyclic state graph."""
        problem = _CyclicProblem()
        goal_node, explored, _ = depth_first_graph_search(problem)
        self.assertIsNotNone(goal_node)
        self.assertTrue(problem.goal_test(goal_node.state))

    def test_returns_none_on_unsolvable(self):
        problem = _IsolatedProblem()
        goal_node, explored, elapsed_ms = depth_first_graph_search(problem)
        self.assertIsNone(goal_node)
        self.assertGreater(len(explored), 0)   # at least the initial state
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_initial_is_goal(self):
        problem = _TrivialProblem()
        goal_node, explored, _ = depth_first_graph_search(problem)
        self.assertIsNotNone(goal_node)
        self.assertEqual(goal_node.state, problem.initial)
        self.assertEqual(goal_node.path_cost, 0)
        self.assertEqual(len(goal_node.solution()), 0)  # no actions needed
        self.assertEqual(explored, [goal_node.state])

    def test_solves_small_levels(self):
        for level in [1, 2, 3, 4]:
            with self.subTest(level=level):
                result = solve(level, 'DFS')
                self.assertTrue(result.solved, f"DFS failed on level {level}")

    def test_explored_does_not_contain_duplicates(self):
        """The explored list should never record the same state twice."""
        problem = Bloxorz(1)
        _, explored, _ = depth_first_graph_search(problem)
        positions = [s.position for s in explored]
        # Convert inner lists to tuples so they are hashable for the set check
        tuples = [tuple(p) for p in positions]
        self.assertEqual(len(tuples), len(set(tuples)))


    def test_solves_advanced_mechanics(self):
        """DFS can solve stages with bridges/switches, fragile tiles, and split blocks."""
        for level in [22, 24, 29]:  # 22: switches/bridges, 24: fragile, 29: split block
            with self.subTest(level=level):
                result = solve(level, 'DFS')
                self.assertTrue(result.solved, f"DFS failed on advanced level {level}")


# ────────────────────────── A* tests ───────────────────────────────

class TestAStar(unittest.TestCase):
    """A*: solvability, optimality, replay, cycles, unsolvable."""

    def test_solves_level_one(self):
        result = solve(1, 'A*')
        self.assertTrue(result.solved)
        self.assertIsNotNone(result.solution_path())
        self.assertGreater(len(result.explored), 0)
        self.assertGreaterEqual(result.elapsed_ms, 0)

    def test_optimal_cost_level_one(self):
        """Level 1 optimal is 4 moves (RIGHT x4 across a flat board).

        start (2,4) -> [3,4,4,4] -> [5,4] -> [6,4,7,4] -> [8,4] = goal
        """
        problem = Bloxorz(1)
        goal_node, _, _ = astar_search(problem, problem.h1)
        self.assertIsNotNone(goal_node)
        self.assertEqual(goal_node.path_cost, 4)

    def test_solution_replays_to_goal(self):
        """Every returned action is legal; the final state passes goal_test."""
        problem = Bloxorz(1)
        goal_node, _, _ = astar_search(problem, problem.h1)
        self.assertIsNotNone(goal_node)

        state = problem.initial
        for action in goal_node.solution():
            self.assertIn(action, problem.actions(state),
                          f"Action {action} not legal in state {state.position}")
            state = problem.result(state, action)

        self.assertTrue(problem.goal_test(state),
                        f"Final state {state.position} is not the goal")

    def test_handles_cycle_and_optimal(self):
        """A* on a cyclic graph still returns optimal cost."""
        problem = _CyclicProblem()
        goal_node, _, _ = astar_search(problem, lambda n: 0)
        self.assertIsNotNone(goal_node)
        self.assertTrue(problem.goal_test(goal_node.state))
        self.assertEqual(goal_node.path_cost, 2)  # A(0)->B(1)->Goal(2)

    def test_returns_none_on_unsolvable(self):
        problem = _IsolatedProblem()
        goal_node, explored, elapsed_ms = astar_search(problem, lambda n: 0)
        self.assertIsNone(goal_node)
        self.assertGreater(len(explored), 0)
        self.assertGreaterEqual(elapsed_ms, 0)

    def test_initial_is_goal(self):
        problem = _TrivialProblem()
        goal_node, explored, _ = astar_search(problem, lambda n: 0)
        self.assertIsNotNone(goal_node)
        self.assertEqual(goal_node.state, problem.initial)
        self.assertEqual(goal_node.path_cost, 0)

        self.assertEqual(explored, [goal_node.state])

    def test_solves_small_levels(self):
        for level in [1, 2, 3, 4]:
            with self.subTest(level=level):
                result = solve(level, 'A*')
                self.assertTrue(result.solved, f"A* failed on level {level}")

    def test_astar_no_worse_than_dfs(self):
        """A* solution cost must be <= DFS solution cost (optimality)."""
        problem = Bloxorz(1)
        astar_node, _, _ = astar_search(problem, problem.h1)
        dfs_node, _, _ = depth_first_graph_search(problem)
        self.assertIsNotNone(astar_node)
        self.assertIsNotNone(dfs_node)
        self.assertLessEqual(astar_node.path_cost, dfs_node.path_cost)

    def test_consistent_h1_does_not_reopen_states_on_level_one(self):
        """This consistent-heuristic case is unique; inconsistent h may reopen."""
        problem = Bloxorz(1)
        _, explored, _ = astar_search(problem, problem.h1)
        self.assertEqual(len(explored), len(set(explored)))

    def test_solves_advanced_mechanics(self):
        """A* can solve stages with bridges/switches, fragile tiles, and split blocks."""
        for level in [22, 24, 29]:  # 22: switches/bridges, 24: fragile, 29: split block
            with self.subTest(level=level):
                result = solve(level, 'A*')
                self.assertTrue(result.solved, f"A* failed on advanced level {level}")
                self.assertIsNotNone(result.solution_path())


# ── Helper Problem subclasses for edge-case tests ─────────────────

class _TrivialProblem(Problem):
    """Initial state is already the goal; no actions available."""

    def __init__(self):
        super().__init__(State([0, 0]), State([0, 0]))

    def actions(self, state):
        return []

    def result(self, state, action):
        return state


class _IsolatedProblem(Problem):
    """Goal is unreachable: no actions from the initial state."""

    def __init__(self):
        super().__init__(State([0, 0]), State([99, 99]))

    def actions(self, state):
        return []

    def result(self, state, action):
        return state


class _CyclicProblem(Problem):
    """A -> B -> A cycle, with B -> Goal.  Optimal cost = 2."""

    def __init__(self):
        super().__init__(State([0, 0]), State([2, 0]))

    def actions(self, state):
        if state.position == [0, 0]:
            return ['RIGHT']
        elif state.position == [1, 0]:
            return ['LEFT', 'RIGHT']
        return []

    def result(self, state, action):
        if state.position == [0, 0] and action == 'RIGHT':
            return State([1, 0])
        if state.position == [1, 0] and action == 'LEFT':
            return State([0, 0])
        if state.position == [1, 0] and action == 'RIGHT':
            return State([2, 0])
        return state


if __name__ == '__main__':
    unittest.main()
