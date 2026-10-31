import json
import os
import tempfile
import unittest
from collections import deque

from engine import Bloxorz, GameSession, Level, State
from engine.algo_implementation.problem import Problem


def make_problem(tiles, start, end, switches=None, splits=None):
    data = {
        "level": 0,
        "size": len(tiles),
        "start": [start[1], start[0]],
        "end": [end[1], end[0]],
        "tiles": tiles,
    }
    if switches is not None:
        data["switches"] = switches
    if splits is not None:
        data["splits"] = splits

    handle, path = tempfile.mkstemp(suffix='.json')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as level_file:
            json.dump(data, level_file)
        level = Level.__new__(Level)
        level.load_level(path)
    finally:
        os.unlink(path)

    problem = Bloxorz.__new__(Bloxorz)
    problem.level = level
    Problem.__init__(problem, State(level.start, level.bridges_open), State(level.end))
    return problem


def bfs(session):
    """Shortest action count, including SWITCH, or None. (Reference, not a graded solver.)"""
    p = session.problem
    seen, queue = {p.initial}, deque([(p.initial, 0)])
    while queue:
        state, d = queue.popleft()
        if p.goal_test(state):
            return d
        for a in p.actions(state):
            nxt = p.result(state, a)
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, d + 1))
    return None


class AdvancedTileTests(unittest.TestCase):
    def test_every_level_is_solvable(self):
        for n in range(1, 58):
            self.assertIsNotNone(bfs(GameSession(n)), 'level {} has no solution'.format(n))

    def test_classic_level_one_takes_seven_moves(self):
        self.assertEqual(bfs(GameSession(21)), 7)

    def test_fragile_tile_breaks_standing_block_but_not_lying_one(self):
        from engine import State
        p = GameSession(24).problem      # classic level 4 has fragile tiles
        kinds = p.level.kinds
        fx, fy = next((x, y) for (x, y), k in kinds.items()
                      if k == 'f' and (x + 1, y) in kinds and (x + 2, y) in kinds)
        lying = State([fx + 1, fy, fx + 2, fy], p.initial.bridges)
        self.assertIsNone(p._move(lying, 'LEFT'))          # would stand up on the fragile tile
        standing = State([fx + 2, fy], p.initial.bridges)
        self.assertIsNotNone(p._move(standing, 'LEFT'))    # lies across it instead

    def test_switch_toggles_bridges_and_split_merges(self):
        s = GameSession(22)          # classic level 2: soft/heavy switches and bridges
        self.assertTrue(s.level.switches and s.level.bridge_index)
        s = GameSession(29)          # classic level 9: a split tile
        self.assertTrue(s.level.splits)
        p = s.problem
        split_states = {p.initial}
        frontier = [p.initial]
        seen_split = False
        while frontier and not seen_split:
            nxt = []
            for st in frontier:
                for a in p.actions(st):
                    ns = p.result(st, a)
                    if ns not in split_states:
                        split_states.add(ns)
                        nxt.append(ns)
                        seen_split = seen_split or ns.split
            frontier = nxt
        self.assertTrue(seen_split, 'no split state reachable')


class FragileTileTests(unittest.TestCase):
    def setUp(self):
        self.problem = make_problem(
            ["bebbb", "bbbbb", "bbfbb", "bbbbb", "bbbbb"],
            (0, 0), (1, 0))
        self.bridges = self.problem.initial.bridges

    def test_rolling_upright_onto_fragile_tile_fails(self):
        lying = State([0, 2, 1, 2], self.bridges)
        self.assertIsNone(self.problem._move(lying, 'RIGHT'))

    def test_lying_block_is_supported_by_fragile_tile(self):
        lying = State([1, 2, 2, 2], self.bridges)
        self.assertIsNotNone(self.problem._move(lying, 'UP'))

    def test_split_cube_is_supported_by_fragile_tile(self):
        split = State([2, 3, 4, 3], self.bridges, True, 0)
        result = self.problem._move(split, 'DOWN')
        self.assertIsNotNone(result)
        self.assertTrue(result.split)
        self.assertEqual(result.position[:2], [2, 2])


class BridgeAndSwitchTests(unittest.TestCase):
    def test_soft_switch_opens_bridge_under_lying_block(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bbslb", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[3, 2, "on"]]}])
        result = problem._move(State([2, 1, 3, 1], problem.initial.bridges), 'UP')
        self.assertIsNotNone(result)
        self.assertEqual(result.bridges, (1,))

    def test_switch_can_close_bridge_under_lying_block(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bbskb", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[3, 2, "off"]]}])
        self.assertEqual(problem.initial.bridges, (1,))
        self.assertIsNone(
            problem._move(State([2, 1, 3, 1], problem.initial.bridges), 'UP'))

    def test_closed_bridge_is_void(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bblbb", "bbbbb", "bbbbb"],
            (0, 0), (1, 0))
        self.assertEqual(problem.initial.bridges, (0,))
        self.assertIsNone(
            problem._move(State([2, 3], problem.initial.bridges), 'DOWN'))

    def test_open_bridge_supports_standing_block(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bbkbb", "bbbbb", "bbbbb"],
            (0, 0), (1, 0))
        self.assertEqual(problem.initial.bridges, (1,))
        self.assertIsNotNone(
            problem._move(State([2, 3], problem.initial.bridges), 'DOWN'))

    def test_soft_switch_activates_for_split_cube(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bbsbl", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[4, 2, "onoff"]]}])
        split = State([1, 3, 2, 3], problem.initial.bridges, True, 1)
        result = problem._move(split, 'DOWN')
        self.assertIsNotNone(result)
        self.assertTrue(result.split)
        self.assertEqual(result.bridges, (1,))

    def test_heavy_switch_requires_standing_block(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bbhbl", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[4, 2, "onoff"]]}])
        standing = problem._move(
            State([0, 2, 1, 2], problem.initial.bridges), 'RIGHT')
        self.assertEqual(standing.bridges, (1,))

        lying = problem._move(
            State([2, 1, 3, 1], problem.initial.bridges), 'DOWN')
        self.assertIsNotNone(lying)
        self.assertEqual(lying.bridges, (0,))

        split = problem._move(
            State([2, 3, 1, 3], problem.initial.bridges, True, 0), 'DOWN')
        self.assertIsNotNone(split)
        self.assertTrue(split.split)
        self.assertEqual(split.bridges, (0,))

    def test_toggle_switch_flips_bridge_each_activation(self):
        problem = make_problem(
            ["bebbb", "bbbbb", "bbsbl", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[4, 2, "onoff"]]}])
        on = problem._move(State([2, 3], problem.initial.bridges), 'DOWN')
        self.assertEqual(on.bridges, (1,))
        off_switch = problem._move(on, 'UP')
        self.assertEqual(off_switch.bridges, (1,))
        on_again = problem._move(off_switch, 'DOWN')
        self.assertEqual(on_again.bridges, (0,))

    def test_permanent_switch_sets_fixed_bridge_state(self):
        on_problem = make_problem(
            ["bebbb", "bbbbb", "bbsbl", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[4, 2, "on"]]}])
        first = on_problem._move(State([2, 3], on_problem.initial.bridges), 'DOWN')
        off_switch = on_problem._move(first, 'UP')
        second = on_problem._move(off_switch, 'DOWN')
        self.assertEqual(first.bridges, (1,))
        self.assertEqual(second.bridges, (1,))

        off_problem = make_problem(
            ["bebbb", "bbbbb", "bbsbk", "bbbbb", "bbbbb"],
            (0, 0), (1, 0),
            switches=[{"at": [2, 2], "bridges": [[4, 2, "off"]]}])
        self.assertEqual(off_problem.initial.bridges, (1,))
        first = off_problem._move(
            State([2, 3], off_problem.initial.bridges), 'DOWN')
        off_switch = off_problem._move(first, 'UP')
        second = off_problem._move(off_switch, 'DOWN')
        self.assertEqual(first.bridges, (0,))
        self.assertEqual(second.bridges, (0,))


class SplitSwitchTests(unittest.TestCase):
    def setUp(self):
        self.tiles = ["bebbb", "bbbbb", "bbvbb", "bbbbb", "bbbbb"]

    def test_split_switch_teleports_to_non_adjacent_cubes(self):
        problem = make_problem(
            self.tiles, (0, 0), (1, 0),
            splits=[{"at": [2, 2], "cubes": [0, 0, 4, 4]}])
        result = problem._move(
            State([0, 2, 1, 2], problem.initial.bridges), 'RIGHT')
        self.assertTrue(result.split)
        self.assertEqual(result.position, [0, 0, 4, 4])

    def test_split_switch_merges_adjacent_teleport_targets(self):
        problem = make_problem(
            self.tiles, (0, 0), (1, 0),
            splits=[{"at": [2, 2], "cubes": [0, 4, 1, 4]}])
        result = problem._move(
            State([0, 2, 1, 2], problem.initial.bridges), 'RIGHT')
        self.assertFalse(result.split)
        self.assertEqual(result.position, [0, 4, 1, 4])

    def test_lying_block_does_not_activate_split_switch(self):
        problem = make_problem(
            self.tiles, (0, 0), (1, 0),
            splits=[{"at": [2, 2], "cubes": [0, 0, 4, 4]}])
        result = problem._move(
            State([2, 3, 3, 3], problem.initial.bridges), 'DOWN')
        self.assertIsNotNone(result)
        self.assertFalse(result.split)
        self.assertEqual(result.position, [2, 2, 3, 2])

    def test_split_cube_does_not_activate_split_switch(self):
        problem = make_problem(
            self.tiles, (0, 0), (1, 0),
            splits=[{"at": [2, 2], "cubes": [0, 0, 4, 4]}])
        result = problem._move(
            State([2, 3, 1, 3], problem.initial.bridges, True, 0), 'DOWN')
        self.assertIsNotNone(result)
        self.assertTrue(result.split)
        self.assertEqual(result.position, [2, 2, 1, 3])


class SplitMovementTests(unittest.TestCase):
    def setUp(self):
        self.problem = make_problem(
            ["bebbb", "bbbbb", "bbbbb", "bbbbb", "bbbbb"],
            (0, 0), (1, 0))
        self.bridges = self.problem.initial.bridges

    def test_switch_toggles_active_cube_without_moving(self):
        state = State([1, 1, 3, 1], self.bridges, True, 0)
        switched = self.problem.result(state, 'SWITCH')
        self.assertTrue(switched.split)
        self.assertEqual(switched.active, 1)
        self.assertEqual(switched.position, state.position)

    def test_switch_action_requires_split_state(self):
        self.assertIsNone(self.problem.result(State([1, 1], self.bridges), 'SWITCH'))

    def test_moving_next_to_other_cube_merges_horizontally(self):
        state = State([1, 1, 3, 1], self.bridges, True, 0)
        result = self.problem.result(state, 'RIGHT')
        self.assertFalse(result.split)
        self.assertEqual(result.position, [2, 1, 3, 1])

    def test_moving_next_to_other_cube_merges_vertically(self):
        state = State([1, 1, 1, 3], self.bridges, True, 0)
        result = self.problem.result(state, 'UP')
        self.assertFalse(result.split)
        self.assertEqual(result.position, [1, 2, 1, 3])

    def test_split_cube_cannot_win(self):
        state = State([1, 1, 3, 1], self.bridges, True, 0)
        result = self.problem.result(state, 'DOWN')
        self.assertTrue(result.split)
        self.assertFalse(self.problem.goal_test(result))

    def test_split_cube_can_rest_on_goal(self):
        state = State([1, 1, 3, 1], self.bridges, True, 0)
        result = self.problem.result(state, 'DOWN')
        self.assertEqual(result.position[:2], [1, 0])
        self.assertFalse(self.problem.goal_test(result))


class StateUniquenessTests(unittest.TestCase):
    def test_bridges_split_and_active_cube_change_state_identity(self):
        split = State([1, 1, 3, 1], (), True, 0)
        switched = State([1, 1, 3, 1], (), True, 1)
        bridged = State([1, 1, 3, 1], (1,), True, 0)
        self.assertEqual(len({split, switched, bridged}), 3)
        self.assertNotEqual(State([1, 1, 2, 1]), split)


class LevelValidationTests(unittest.TestCase):
    def test_unknown_tile_character_is_rejected(self):
        with self.assertRaises(ValueError):
            make_problem(["bebbb", "bbbbb", "bbxbb", "bbbbb", "bbbbb"],
                         (0, 0), (1, 0))

    def test_end_must_be_goal_tile(self):
        with self.assertRaises(ValueError):
            make_problem(["bbbbb", "bbbbb", "bbbbb", "bbbbb", "bbbbb"],
                         (0, 0), (1, 0))

    def test_switch_requires_valid_bridge(self):
        with self.assertRaises(ValueError):
            make_problem(
                ["bebbb", "bbbbb", "bbsbl", "bbbbb", "bbbbb"],
                (0, 0), (1, 0),
                switches=[{"at": [2, 2], "bridges": [[0, 4, "on"]]}])

    def test_switch_requires_valid_mode(self):
        with self.assertRaises(ValueError):
            make_problem(
                ["bebbb", "bbbbb", "bbsbl", "bbbbb", "bbbbb"],
                (0, 0), (1, 0),
                switches=[{"at": [2, 2], "bridges": [[4, 2, "sideways"]]}])

    def test_split_targets_must_be_distinct(self):
        with self.assertRaises(ValueError):
            make_problem(
                ["bebbb", "bbbbb", "bbvbb", "bbbbb", "bbbbb"],
                (0, 0), (1, 0),
                splits=[{"at": [2, 2], "cubes": [0, 4, 0, 4]}])

    def test_split_targets_must_be_on_tiles(self):
        with self.assertRaises(ValueError):
            make_problem(
                ["bebbb", "bbbbb", "bbvbb", "bbbbb", "bbbbb"],
                (0, 0), (1, 0),
                splits=[{"at": [2, 2], "cubes": [0, 4, 9, 9]}])

    def test_switch_must_be_on_switch_tile(self):
        with self.assertRaises(ValueError):
            make_problem(
                ["bebbb", "bbbbb", "bbsbl", "bbbbb", "bbbbb"],
                (0, 0), (1, 0),
                switches=[{"at": [3, 2], "bridges": [[4, 2, "on"]]}])


if __name__ == '__main__':
    unittest.main()
