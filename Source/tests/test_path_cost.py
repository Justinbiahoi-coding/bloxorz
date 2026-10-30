"""Fragile penalties on legal, reachable Bloxorz transitions and real searches."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_bfs_levels import check_level, fragile_landing
from engine import GameSession, solve
from engine.algo_implementation.problem import Problem


class PathCostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'levels').mkdir()
        self.patch = patch('engine.level.BASE_DIR', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.level_id = 0

    def make_level(self, fragile=(), targets=None, size=7, goal=(6, 6)):
        """Use the real JSON loader; fixtures live outside the game's catalog."""
        rows = [list('b' * size) for _ in range(size)]
        for x, y in fragile:
            rows[y][x] = 'f'
        rows[goal[1]][goal[0]] = 'e'
        data = {'level': self.level_id, 'size': size, 'start': [3, 0],
                'end': list(reversed(goal)), 'tiles': None}
        if targets is not None:
            rows[3][3] = 'v'
            data['splits'] = [{'at': [3, 3], 'cubes': list(targets)}]
        data['tiles'] = [''.join(row) for row in rows]
        level_id = self.level_id
        self.level_id += 1
        (self.root / 'levels' / '{}.json'.format(level_id)).write_text(
            json.dumps(data), encoding='utf-8')
        return level_id

    def walk(self, session, *actions):
        for action in actions:
            self.assertIn(action, session.actions())
            self.assertTrue(session.move(action))

    def split_session(self, fragile=(), targets=(1, 1, 5, 1)):
        session = GameSession(self.make_level(fragile, targets))
        self.walk(session, 'RIGHT', 'RIGHT')
        return session

    def assert_step_cost(self, session, action, expected):
        self.assertIn(action, session.actions())
        before = session.state
        self.assertTrue(session.move(action))
        after = session.state
        snapshots = [copy.deepcopy(vars(state)) for state in (before, after)]
        hashes = [hash(before), hash(after)]
        keys = {before, after}
        board = copy.deepcopy(vars(session.level))
        self.assertEqual(1 + 2 * fragile_landing(session.level, before, action, after), expected)
        for accumulated in (0, 11):
            self.assertEqual(
                session.problem.path_cost(accumulated, before, action, after),
                accumulated + expected)
        self.assertEqual([vars(before), vars(after)], snapshots)
        self.assertEqual([hash(before), hash(after)], hashes)
        self.assertIn(before, keys)
        self.assertIn(after, keys)
        self.assertEqual(vars(session.level), board)

    def test_normal_move_costs_one(self):
        session = GameSession(self.make_level())
        self.assert_step_cost(session, 'RIGHT', 1)

    def test_one_or_two_fragile_tiles_cost_three_once(self):
        for fragile in (((1, 3),), ((1, 3), (2, 3))):
            with self.subTest(fragile=fragile):
                session = GameSession(self.make_level(fragile))
                self.assert_step_cost(session, 'RIGHT', 3)

    def test_leaving_fragile_costs_one(self):
        session = GameSession(self.make_level(((1, 3), (2, 3))))
        self.walk(session, 'RIGHT')
        self.assert_step_cost(session, 'UP', 1)

    def test_consecutive_moves_on_fragile_each_pay_surcharge(self):
        session = GameSession(self.make_level(((1, 3), (2, 3), (1, 4), (2, 4))))
        self.assert_step_cost(session, 'RIGHT', 3)
        self.assert_step_cost(session, 'UP', 3)
        self.assert_step_cost(session, 'DOWN', 3)

    def test_switch_costs_one_with_cube_on_fragile(self):
        session = self.split_session(((1, 1),))
        self.assertTrue(session.is_split)
        self.assert_step_cost(session, 'SWITCH', 1)

    def test_stationary_fragile_cube_does_not_add_surcharge(self):
        session = self.split_session(((1, 1),))
        self.walk(session, 'SWITCH')
        self.assertEqual(session.active, 1)
        self.assert_step_cost(session, 'UP', 1)

    def test_each_active_cube_pays_for_its_own_fragile_destination(self):
        for active, fragile in ((0, (1, 2)), (1, (5, 2))):
            with self.subTest(active=active):
                session = self.split_session((fragile,))
                if active:
                    self.walk(session, 'SWITCH')
                self.assert_step_cost(session, 'UP', 3)

    def test_split_cube_leaving_fragile_costs_one(self):
        session = self.split_session(((1, 1),))
        self.assert_step_cost(session, 'UP', 1)

    def test_merge_uses_moved_cube_even_when_coordinates_are_reordered(self):
        cases = [
            ((5, 1, 2, 1), 0, 'LEFT', (2, 1), (3, 1)),
            ((2, 1, 5, 1), 1, 'LEFT', (2, 1), (3, 1)),
            ((1, 5, 1, 2), 0, 'DOWN', (1, 2), (1, 3)),
            ((1, 2, 1, 5), 1, 'DOWN', (1, 2), (1, 3)),
        ]
        for targets, active, action, stationary, destination in cases:
            for fragile, expected in ((stationary, 1), (destination, 3)):
                with self.subTest(targets=targets, active=active, fragile=fragile):
                    session = self.split_session((fragile,), targets)
                    if active:
                        self.walk(session, 'SWITCH')
                    self.walk(session, action)
                    self.assertTrue(session.is_split)
                    self.assert_step_cost(session, action, expected)
                    self.assertFalse(session.is_split)
                    self.assertIn(destination, session.block_cells())

    def test_teleport_checks_both_destinations_and_charges_once(self):
        for fragile in ((), ((1, 1),), ((5, 1),), ((1, 1), (5, 1))):
            with self.subTest(fragile=fragile):
                session = GameSession(self.make_level(fragile, (1, 1, 5, 1)))
                self.walk(session, 'RIGHT')
                self.assert_step_cost(session, 'RIGHT', 3 if fragile else 1)
                self.assertTrue(session.is_split)

    def test_teleport_with_adjacent_targets_still_checks_both_cells(self):
        for fragile in (((3, 1),), ((4, 1),), ((3, 1), (4, 1))):
            with self.subTest(fragile=fragile):
                session = GameSession(self.make_level(fragile, (4, 1, 3, 1)))
                self.walk(session, 'RIGHT')
                self.assert_step_cost(session, 'RIGHT', 3)
                self.assertFalse(session.is_split)
                self.assertEqual(session.state.position, [3, 1, 4, 1])

    def test_bridges_and_switches_have_no_extra_penalty(self):
        level_id = self.make_level()
        path = self.root / 'levels' / '{}.json'.format(level_id)
        data = json.loads(path.read_text(encoding='utf-8'))
        rows = [list(row) for row in data['tiles']]
        rows[3][1:4] = ['s', 'k', 'h']
        data['tiles'] = [''.join(row) for row in rows]
        data['switches'] = [
            {'at': [1, 3], 'bridges': [[2, 3, 'on']]},
            {'at': [3, 3], 'bridges': [[2, 3, 'off']]},
        ]
        path.write_text(json.dumps(data), encoding='utf-8')
        session = GameSession(level_id)
        self.assert_step_cost(session, 'RIGHT', 1)
        self.assert_step_cost(session, 'RIGHT', 1)

    def test_fragile_standing_remains_illegal(self):
        session = GameSession(self.make_level(((3, 3),)))
        self.walk(session, 'RIGHT')
        self.assertNotIn('RIGHT', session.actions())
        self.assertFalse(session.move('RIGHT'))

    def test_generic_problem_keeps_unit_cost(self):
        self.assertEqual(Problem(None).path_cost(7, None, 'SWITCH', None), 8)

    def test_audit_replays_and_checks_cost_for_each_real_solver(self):
        level_id = self.make_level(
            tuple((x, 3) for x in (1, 2, 4, 5, 7, 8)), size=10, goal=(9, 3))
        for name in ('BFS', 'UCS', 'A*'):
            with self.subTest(algorithm=name):
                row = check_level(level_id, name)
                self.assertEqual(row['status'], 'SOLVED', row)
                self.assertEqual(row['cost'], row['replay_cost'])
                self.assertEqual(row['cost'], row['actions'] + 2 * row['surcharged_actions'])

    def test_audit_reports_incorrect_solver_cost_as_replay_error(self):
        level_id = self.make_level()
        result = solve(level_id, 'BFS', measure_memory=False)
        result.goal_node.path_cost += 1
        with patch('engine.solve', return_value=result):
            row = check_level(level_id)
        self.assertEqual(row['status'], 'REPLAY_ERROR')
        self.assertIn('Cost mismatch', row['error'])
        self.assertIn('traceback', row)

    def test_real_bfs_minimizes_actions_and_ucs_minimizes_penalized_cost(self):
        # Direct: six rolls, three landings on fragile (cost 12).
        # Detour: ten rolls on ordinary floor (cost 10).
        level_id = self.make_level(
            tuple((x, 3) for x in (1, 2, 4, 5, 7, 8)), size=10, goal=(9, 3))
        results = {name: solve(level_id, name, measure_memory=False)
                   for name in ('BFS', 'Uniform Cost Search')}
        self.assertEqual((results['BFS'].solution_length, results['BFS'].solution_cost), (6, 12))
        self.assertEqual((results['Uniform Cost Search'].solution_length,
                          results['Uniform Cost Search'].solution_cost), (10, 10))
        for name, result in results.items():
            with self.subTest(algorithm=name):
                session = GameSession(level_id)
                surcharges = 0
                actions = result.goal_node.solution()
                for action in actions:
                    self.assertIn(action, session.actions())
                    self.assertTrue(session.move(action))
                    # Independent of path_cost: this fixture never splits.
                    surcharges += any(session.level.kinds[cell] == 'f'
                                      for cell in session.block_cells())
                self.assertTrue(session.won)
                self.assertEqual(result.solution_cost, len(actions) + 2 * surcharges)
                self.assertEqual(surcharges, 3 if name == 'BFS' else 0)
                self.assertEqual(result.goal_node.depth, len(actions))


if __name__ == '__main__':
    unittest.main()
