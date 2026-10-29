import tracemalloc
import unittest

from engine import Bloxorz, solve, solve_problem


class MetricTests(unittest.TestCase):
    """The four numbers the report needs: time, peak memory, expanded nodes, solution length."""

    def test_solve_reports_all_four_metrics(self):
        result = solve(1, 'BFS')
        self.assertGreaterEqual(result.elapsed_ms, 0)
        self.assertGreater(result.peak_memory_kb, 0)
        self.assertEqual(result.expanded, len(result.explored))
        self.assertEqual(result.solution_length, len(result.solution_path()) - 1)
        self.assertEqual(result.solution_length, len(result.goal_node.solution()))

    def test_memory_is_skipped_unless_asked(self):
        result = solve_problem(Bloxorz(1), 'BFS')
        self.assertIsNone(result.peak_memory_kb)

    def test_bigger_search_uses_more_memory(self):
        small = solve(1, 'BFS').peak_memory_kb
        large = solve(46, 'BFS').peak_memory_kb
        self.assertGreater(large, small)

    def test_leaves_an_outer_trace_running(self):
        tracemalloc.start()
        try:
            solve(1, 'A*')
            self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()

    def test_unsolved_result_has_no_length(self):
        result = solve(1, 'BFS')
        result.goal_node = None
        self.assertIsNone(result.solution_length)


if __name__ == '__main__':
    unittest.main()
