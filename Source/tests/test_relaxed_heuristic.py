"""Exhaustive small real-engine graphs, checked against independent oracles."""
from collections import deque
import copy
import heapq
from itertools import count
import json
from math import inf, isfinite
from pathlib import Path
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

from check_bfs_levels import fragile_landing
from engine import GameSession, State, solve_problem
from engine.algo_implementation.node import Node
from engine.heuristic import board_key, relaxed_distances
from engine.search_model import _RollProblem


def point_oracle(level):
    """Independent all-pairs Floyd-Warshall, with FORWARD teleport edges."""
    cells = list(level.kinds)
    distance = {a: {b: 0 if a == b else inf for b in cells} for a in cells}
    for a in cells:
        for b in cells:
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1:
                distance[a][b] = 1
    for trigger, targets in level.splits.items():
        for target in zip(targets[::2], targets[1::2]):
            distance[trigger][target] = 0
    for middle in cells:
        for a in cells:
            for b in cells:
                distance[a][b] = min(distance[a][b], distance[a][middle] + distance[middle][b])
    return distance


class RelaxedHeuristicTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'levels').mkdir()
        patcher = patch('engine.level.BASE_DIR', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.level_id = 0

    def session(self, rows, start, goal, splits=(), switches=()):
        data = dict(level=self.level_id, size=len(rows), tiles=rows,
                    start=list(reversed(start)), end=list(reversed(goal)),
                    splits=list(splits), switches=list(switches))
        (self.root / 'levels' / '{}.json'.format(self.level_id)).write_text(json.dumps(data), encoding='utf-8')
        session = GameSession(self.level_id)
        self.level_id += 1
        return session

    def shortcut(self):
        return self.session(['          ', 'bbbv   bbe'] + ['          '] * 8,
                            (0, 1), (9, 1), splits=[{'at': [3, 1], 'cubes': [7, 1, 8, 1]}])

    def audit(self, session):
        """Enumerate primitive-reachable states; oracle costs use reverse Dijkstra.

        Edge costs are independently audited with the moved-cell fragile rule,
        rather than taking UCS or A* as the optimal-cost oracle.
        """
        problem, model = session.problem, _RollProblem(session.problem)
        seen, pending, primitive_edges = {problem.initial}, deque([problem.initial]), []
        while pending:
            state = pending.popleft()
            if problem.goal_test(state):
                continue
            for action in problem.actions(state):
                after = problem.result(state, action)
                cost = 1 + 2 * fragile_landing(problem.level, state, action, after)
                primitive_edges.append((state, after, cost))
                if after not in seen:
                    seen.add(after)
                    pending.append(after)

        reverse, edges, features = {s: [] for s in seen}, [], set()
        for state in seen:
            if state.split:
                features.add('split')
            if len(state.position) == 2:
                features.add('standing')
            elif not state.split:
                features.add('lying')
            if problem.goal_test(state):
                continue
            for edge in model.actions(state):
                cursor, cost = state, 0
                for action in edge:
                    after = problem.result(cursor, action)
                    cost += 1 + 2 * fragile_landing(problem.level, cursor, action, after)
                    cursor = after
                self.assertIn(cursor, seen)
                self.assertEqual(model.result(state, edge), cursor)
                self.assertEqual(model.path_cost(0, state, edge, cursor), cost)
                edges.append((state, cursor, cost))
                reverse[cursor].append((state, cost))
                if len(edge) == 2:
                    features.add('select_then_roll')
                if state.split and not cursor.split:
                    features.add('merge')
                if not state.split and cursor.split:
                    features.add('teleport_split')
                if state.bridges != cursor.bridges:
                    features.add('toggle')
                    if (not cursor.split and len(cursor.position) == 2
                            and problem.level.kinds.get(tuple(cursor.position)) == 'h'):
                        features.add('heavy_toggle')
                if cost > len(edge):
                    features.add('fragile')

        goals = [s for s in seen if problem.goal_test(s)]
        optimal = {s: 0 for s in goals}
        order = count()
        queue = [(0, next(order), s) for s in goals]
        heapq.heapify(queue)
        while queue:
            cost, _, state = heapq.heappop(queue)
            if cost != optimal[state]:
                continue
            for before, step in reverse[state]:
                candidate = cost + step
                if candidate < optimal.get(before, inf):
                    optimal[before] = candidate
                    heapq.heappush(queue, (candidate, next(order), before))

        points = point_oracle(problem.level)
        table = relaxed_distances(board_key(problem.level, problem.goal))
        goal_cell = tuple(problem.goal.position)
        self.assertEqual(table, {cell: distances[goal_cell] for cell, distances in points.items()})
        values = {}
        for state in seen:
            snapshot, key = copy.deepcopy(vars(state)), hash(state)
            h = values[state] = problem.h1(Node(state))
            self.assertLessEqual(h, optimal.get(state, inf))
            self.assertEqual(vars(state), snapshot)
            self.assertEqual(hash(state), key)
            if problem.goal_test(state):
                self.assertEqual(h, 0)
        for before, after, cost in primitive_edges + edges:
            self.assertLessEqual(values[before], cost + values[after])
            sources = list(zip(before.position[::2], before.position[1::2]))
            for target in zip(after.position[::2], after.position[1::2]):
                self.assertLessEqual(min(points[source][target] for source in sources), 2)

        return dict(states=len(seen), rolling_edges=len(edges), primitive_edges=len(primitive_edges),
                    finite_optima=len(optimal), features=sorted(features))

    def test_exhaustive_normal_states_edges_admissibility_and_consistency(self):
        session = self.session(['bbbbb', 'bbbbb', 'bbfbb', 'bbbbb', 'bbbbe'], (0, 0), (4, 4))
        self.audit_stats = self.audit(session)
        self.assertTrue({'standing', 'lying', 'fragile'} <= set(self.audit_stats['features']))

    def test_exhaustive_split_merge_switch_bridge_and_fragile_graph(self):
        session = self.session(['      ', 'bbbv  ', ' bbh  ', ' bbfbe', ' bbsll', ' bbbbb'],
                               (0, 1), (5, 3), splits=[{'at': [3, 1], 'cubes': [1, 3, 4, 3]}],
                               switches=[{'at': [3, 4], 'bridges': [[4, 4, 'onoff']]},
                                         {'at': [3, 2], 'bridges': [[5, 4, 'onoff']]}])
        self.audit_stats = self.audit(session)
        self.assertTrue({'split', 'merge', 'select_then_roll', 'toggle', 'heavy_toggle', 'fragile', 'teleport_split'}
                        <= set(self.audit_stats['features']))
        self.assertGreater(self.audit_stats['finite_optima'], 0)

    def test_teleport_shortcut_defeats_old_manhattan_before_any_split_state(self):
        session = self.shortcut()
        problem = session.problem
        old_h = abs(problem.goal.position[0] - problem.initial.position[0]) // 2
        self.assertEqual(old_h, 4)
        self.assertEqual(problem.h1(Node(problem.initial)), 2)
        self.audit_stats = self.audit(session)
        for algorithm in ('BFS', 'Uniform Cost Search', 'A*'):
            session.reset()
            result = solve_problem(problem, algorithm)
            self.assertEqual((result.solution_length, result.solution_cost), (3, 3))
            self.assertEqual(result.solution_path()[2].state.position, [7, 1, 8, 1])
            for action, node in zip(result.goal_node.solution(), result.solution_path()[1:]):
                self.assertTrue(session.move(action))
                self.assertEqual(session.state, node.state)
                self.assertEqual(session.cost, node.path_cost)
            self.assertTrue(session.won)
            self.assertFalse(any(node.state.split for node in result.solution_path()))
        self.assertGreater(old_h, session.cost)

    def test_teleport_edges_are_directed_and_infinity_is_preserved(self):
        session = self.session(['          ', 'ebbv   bbb'] + ['          '] * 8,
                               (1, 1), (0, 1), splits=[{'at': [3, 1], 'cubes': [7, 1, 8, 1]}])
        problem = session.problem
        self.assertEqual(problem.h1(Node(State([3, 1]))), 2)
        self.assertEqual(problem.h1(Node(State([8, 1]))), inf)
        self.assertEqual(relaxed_distances(board_key(problem.level, problem.goal))[(7, 1)], inf)
        self.audit_stats = self.audit(session)

    def test_unreachable_relaxed_component_is_an_unsolvable_search(self):
        session = self.session(['b  ', '   ', '  e'], (0, 0), (2, 2))
        self.assertEqual(session.problem.h1(Node(session.state)), inf)
        result = solve_problem(session.problem, 'A*')
        self.assertFalse(result.solved)
        self.assertEqual(result.expanded, 1)

    def test_split_active_and_bridge_flags_do_not_change_point_estimate(self):
        session = self.session(['      ', 'bbbv  ', ' bbb  ', ' bbfbe', ' bbsll', ' bbbbb'],
                               (0, 1), (5, 3), splits=[{'at': [3, 1], 'cubes': [1, 3, 4, 3]}],
                               switches=[{'at': [3, 4], 'bridges': [[4, 4, 'onoff']]}])
        for action in ('RIGHT', 'RIGHT'):
            self.assertTrue(session.move(action))
        problem, before = session.problem, session.state
        value = problem.h1(Node(before))
        self.assertGreater(value, 0)
        self.assertTrue(session.move('SWITCH'))
        self.assertEqual(problem.h1(Node(session.state)), value)
        toggled = State(before.position, (1, 1), before.split, before.active)
        self.assertEqual(problem.h1(Node(toggled)), value)
        table = relaxed_distances(board_key(problem.level, problem.goal))
        self.assertTrue(isfinite(table[(3, 3)]))  # fragile is potential floor
        self.assertTrue(isfinite(table[(4, 4)]))  # a closed bridge is open in relaxation

    def test_cache_keys_board_goal_not_hint_initial_and_invalidates_on_changes(self):
        session = self.shortcut()
        problem = session.problem
        problem.h1(Node(session.state))
        cached = problem._relaxed_cache
        self.assertTrue(session.move('RIGHT'))
        problem.initial = session.state
        problem.h1(Node(session.state))
        self.assertIs(problem._relaxed_cache, cached)
        problem.goal = State([0, 1])
        self.assertEqual(problem.h1(Node(State([8, 1]))), inf)
        self.assertIsNot(problem._relaxed_cache, cached)
        cached = problem._relaxed_cache
        problem.level.splits[(3, 1)] = [1, 1, 2, 1]
        problem.h1(Node(session.state))
        self.assertIsNot(problem._relaxed_cache, cached)
        cached = problem._relaxed_cache
        problem.level.kinds[(4, 1)] = 'b'
        problem.h1(Node(session.state))
        self.assertIsNot(problem._relaxed_cache, cached)
        other = self.session(['bbe', 'bbb', 'bbb'], (0, 0), (2, 0)).problem
        self.assertEqual(other.h1(Node(other.initial)), 1)
        self.assertIsNot(other._relaxed_cache, problem._relaxed_cache)

    def test_timing_and_traced_runs_each_build_a_fresh_table(self):
        problem = self.shortcut().problem
        problem.h1(Node(problem.initial))  # a prior warm cache must not hide build cost
        flags = []
        initially_traced = tracemalloc.is_tracing()
        def build(key):
            flags.append(tracemalloc.is_tracing())
            return relaxed_distances(key)
        with patch('engine.problem.relaxed_distances', side_effect=build):
            result = solve_problem(problem, 'A*', measure_memory=True)
        self.assertEqual(flags, [initially_traced, True])
        self.assertTrue(result.solved)
        self.assertGreater(result.peak_memory_kb, 0)


if __name__ == '__main__':
    unittest.main()
