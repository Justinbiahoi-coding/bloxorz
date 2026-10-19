import unittest

from engine import (ALGORITHM_NAMES, GameSession, Level, solve,
                    solve_problem)


class LevelTests(unittest.TestCase):
    def test_all_levels_load(self):
        for level_number in range(1, 21):
            level = Level(level_number)
            self.assertGreater(level.size, 0)
            self.assertEqual(len(level.map), level.size)


class SearchTests(unittest.TestCase):
    def test_all_algorithms_solve_level_one(self):
        for algorithm in ALGORITHM_NAMES:
            result = solve(1, algorithm)
            self.assertTrue(result.solved, algorithm)
            self.assertTrue(result.explored, algorithm)
            self.assertGreaterEqual(result.elapsed_ms, 0)
            self.assertIsNotNone(result.solution_path())

    def test_solution_path_reaches_goal(self):
        result = solve(1, 'BFS')
        session = GameSession(1)
        for action in result.goal_node.solution():
            self.assertTrue(session.move(action))
        self.assertTrue(session.won)


class SessionTests(unittest.TestCase):
    def test_moves_update_state_and_counter(self):
        session = GameSession(1)
        start = session.state
        self.assertTrue(session.move('RIGHT'))
        self.assertEqual(session.moves, 1)
        self.assertNotEqual(session.state.position, start.position)

    def test_hint_is_next_state_and_cleared_on_move(self):
        session = GameSession(1)
        hint = session.request_hint()
        self.assertIsNotNone(hint)
        self.assertIsNotNone(hint.state.position)
        session.move('RIGHT')
        self.assertIsNone(session.hint)

    def test_solve_from_current_state(self):
        session = GameSession(1)
        session.move('RIGHT')
        result = solve_problem(
            session.problem, 'Uniform Cost Search', initial=session.state)
        self.assertTrue(result.solved)


if __name__ == '__main__':
    unittest.main()
