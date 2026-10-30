"""Bloxorz integration: rolling edges, primitive replay, session cost and engine rules.

Uses real solvers/transitions. Temporary levels remain outside the game catalog;
helper mixins contain no test methods, and imported test modules provide fixtures only.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_bfs_levels import fragile_landing
from engine import GameSession, SolveResult, Tower, solve, solve_problem
from engine.algo_implementation import algorithms
from engine.algo_implementation.node import Node
from engine.search_model import _PrimitiveNodes, _RollProblem
from test_advanced import make_problem
import test_bfs as graph_tests
import test_ucs as graphs



def session_for(problem):
    session = GameSession.__new__(GameSession)
    session.problem, session.level, session.goal = problem, problem.level, problem.goal
    session.level_number = 0
    session.reset()
    return session


def switch_problem(targets=None, stationary_bridge=False, landing_switch=None):
    rows = [list('b' * 7) for _ in range(7)]
    rows[6][6] = 'e'
    switches, splits = [], None
    if targets is None:
        # RIGHT reaches a horizontal block; UP would close its supporting bridge.
        start = (1, 1)
        rows[2][2], rows[2][3] = 's', 'k'
        switches.append({'at': [2, 2], 'bridges': [[3, 2, 'onoff']]})
    else:
        start = (0, 3)
        rows[3][3] = 'v'
        splits = [{'at': [3, 3], 'cubes': list(targets)}]
        if stationary_bridge:
            rows[1][1], rows[1][3] = 'k', 's'
            switches.append({'at': [3, 1], 'bridges': [[1, 1, 'onoff']]})
        else:
            rows[1][1], rows[0][6] = 's', 'l'
            switches.append({'at': [1, 1], 'bridges': [[6, 0, 'onoff']]})
            if landing_switch:
                rows[1][2], rows[1][6] = landing_switch, 'l'
                switches.append({'at': [2, 1], 'bridges': [[6, 1, 'onoff']]})
    return make_problem([''.join(row) for row in rows], start, (6, 6), switches=switches, splits=splits)


def fixture_session(fragile=(), split=False):
    rows = [list('b' * 7) for _ in range(7)]
    for x, y in fragile:
        rows[y][x] = 'f'
    rows[6][6] = 'e'
    splits = None
    if split:
        rows[3][3] = 'v'
        splits = [{'at': [3, 3], 'cubes': [1, 1, 5, 1]}]
    problem = make_problem([''.join(row) for row in rows], (0, 3), (6, 6), splits=splits)
    session = GameSession.__new__(GameSession)
    session.problem, session.level, session.goal = problem, problem.level, problem.goal
    session.level_number = 0
    session.reset()
    return session


class _GameAssertions:
    """Shared legal-transition assertion; never collected as a TestCase."""

    def walk(self, session, actions):
        for action in actions:
            self.assertIn(action, session.actions())
            self.assertTrue(session.move(action))


class _RollingFixture(_GameAssertions):
    """Temporary level and primitive-path helpers, with no inherited tests."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'levels').mkdir()
        patcher = patch('engine.level.BASE_DIR', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.level_id = 0

    def session(self, tiles=None, targets=None, fragile=(), goal=(6, 6), start=(0, 3)):
        rows = [list(row) for row in tiles] if tiles else [list('b' * 7) for _ in range(7)]
        for x, y in fragile:
            rows[y][x] = 'f'
        rows[goal[1]][goal[0]] = 'e'
        data = dict(level=self.level_id, size=len(rows), start=list(reversed(start)),
                    end=list(reversed(goal)))
        if targets:
            rows[3][3] = 'v'
            data['splits'] = [{'at': [3, 3], 'cubes': list(targets)}]
        data['tiles'] = [''.join(row) for row in rows]
        path = self.root / 'levels' / '{}.json'.format(self.level_id)
        path.write_text(json.dumps(data), encoding='utf-8')
        session = GameSession(self.level_id)
        self.level_id += 1
        return session

    def tradeoff(self):
        return self.session(
            tiles=[' b  bbb', 'bb bbbb', 'b bbbbb', 'bbbvbb ',
                   ' be bbb', '  bbbb ', 'bb bbb '],
            targets=(4, 6, 5, 3), goal=(2, 4))

    def replay(self, session, result):
        path, actions = result.solution_path(), result.goal_node.solution()
        spent, rolls, count = session.cost, session.moves, session.action_count
        self.assertEqual(path[0].state, session.state)
        self.assertEqual((path[0].depth, path[0].path_cost), (0, 0))
        self.assertEqual(len(path), len(actions) + 1)
        surcharge = 0
        for i, (action, node) in enumerate(zip(actions, path[1:]), 1):
            self.assertIsInstance(action, str)
            before = session.state
            self.walk(session, [action])
            surcharge += fragile_landing(session.level, before, action, session.state)
            self.assertIs(node.parent, path[i - 1])
            self.assertEqual((node.state, node.action, node.depth), (session.state, action, i))
            self.assertEqual(node.path_cost, session.cost - spent)
        self.assertTrue(session.won)
        self.assertEqual(result.action_count, len(actions))
        self.assertEqual(result.solution_length, sum(a != 'SWITCH' for a in actions))
        self.assertEqual((session.moves - rolls, session.action_count - count),
                         (result.solution_length, result.action_count))
        self.assertEqual(result.solution_cost, len(actions) + 2 * surcharge)
        self.assertEqual(session.cost, spent + result.solution_cost)


class RollingModelTests(_RollingFixture, unittest.TestCase):
    """One search edge per roll; compound costs, legal effects and generic Problems."""

    def test_compound_edge_cost_calls_each_primitive_with_its_intermediate_state(self):
        session = self.session(targets=(1, 1, 5, 1), fragile=((5, 2),))
        self.walk(session, ['RIGHT', 'RIGHT'])
        before, model = session.state, _RollProblem(session.problem)
        edge = ('SWITCH', 'UP')
        self.assertIn(edge, model.actions(before))
        switched = session.problem.result(before, 'SWITCH')
        after = model.result(before, edge)
        with patch.object(session.problem, 'path_cost', wraps=session.problem.path_cost) as cost:
            self.assertEqual(model.path_cost(7, before, edge, after), 11)
        calls = cost.call_args_list
        self.assertEqual([call.args for call in calls],
                         [(7, before, 'SWITCH', switched), (8, switched, 'UP', after)])
        internal = Node(before).child_node(model, edge)
        self.assertEqual((internal.depth, internal.path_cost), (1, 4))
        converter = _PrimitiveNodes(model)
        with patch.object(session.problem, 'path_cost', wraps=session.problem.path_cost) as cost:
            public = converter.convert(internal)
            self.assertIs(converter.convert(internal), public)
            self.assertEqual(cost.call_count, 2)  # the shared chain is converted once
        self.assertEqual(public.solution(), ['SWITCH', 'UP'])
        self.assertEqual([n.state for n in public.path()], [before, switched, after])
        self.assertEqual([n.path_cost for n in public.path()], [0, 1, 4])
        self.assertEqual(public.depth, 2)

    def test_active_cube_roll_needs_no_extra_switch_and_generation_is_immutable(self):
        session = self.session(targets=(1, 1, 5, 1))
        self.walk(session, ['RIGHT', 'RIGHT'])
        state, model = session.state, _RollProblem(session.problem)
        snapshot, board, key = copy.deepcopy(vars(state)), copy.deepcopy(vars(session.level)), hash(state)
        known = {state}
        children = Node(state).expand(model)
        self.assertNotIn(('SWITCH',), model.actions(state))
        self.assertIn('SWITCH', session.actions())  # manual play remains primitive
        direct = next(n for n in children if n.action == ('UP',))
        public = _PrimitiveNodes(model).convert(direct)
        self.assertEqual((public.solution(), public.depth, public.path_cost), (['UP'], 1, 1))
        self.assertEqual(vars(state), snapshot)
        self.assertEqual(vars(session.level), board)
        self.assertEqual(hash(state), key)
        self.assertIn(state, known)
        switched = session.problem.result(state, 'SWITCH')
        self.assertNotEqual(state, switched)
        self.assertEqual(len({state, switched}), 2)

    def test_merge_cost_checks_the_moving_cube_after_selecting_it(self):
        for fragile, expected in (((3, 1), 4), ((2, 1), 2)):
            with self.subTest(fragile=fragile):
                session = self.session(targets=(2, 1, 5, 1), fragile=(fragile,))
                self.walk(session, ['RIGHT', 'RIGHT', 'SWITCH', 'LEFT', 'SWITCH'])
                model = _RollProblem(session.problem)
                node = Node(session.state).child_node(model, ('SWITCH', 'LEFT'))
                self.assertFalse(node.state.split)
                self.assertEqual(node.state.position, [2, 1, 3, 1])
                public = _PrimitiveNodes(model).convert(node)
                self.assertEqual(public.solution(), ['SWITCH', 'LEFT'])
                self.assertEqual(public.path_cost, expected)

    def test_teleport_is_one_roll_with_both_fragile_destinations_checked(self):
        session = self.session(targets=(1, 1, 5, 1), fragile=((1, 1), (5, 1)))
        self.walk(session, ['RIGHT'])
        model = _RollProblem(session.problem)
        self.assertTrue(all(len(edge) == 1 for edge in model.actions(session.state)))
        node = Node(session.state).child_node(model, ('RIGHT',))
        self.assertTrue(node.state.split)
        public = _PrimitiveNodes(model).convert(node)
        self.assertEqual((public.solution(), public.path_cost, public.depth), (['RIGHT'], 3, 1))

    def test_macro_actions_keep_bridge_support_and_stationary_switch_rules(self):
        session = session_for(switch_problem())
        self.walk(session, ['RIGHT'])
        self.assertNotIn(('UP',), _RollProblem(session.problem).actions(session.state))
        session = session_for(switch_problem((1, 2, 4, 1)))
        self.walk(session, ['RIGHT', 'RIGHT', 'DOWN', 'SWITCH', 'LEFT', 'SWITCH'])
        model = _RollProblem(session.problem)
        edge = ('SWITCH', 'LEFT')
        self.assertIn(edge, model.actions(session.state))
        merged = model.result(session.state, edge)
        self.assertFalse(merged.split)
        self.assertEqual(merged.bridges, (1,))

    def test_generic_problems_keep_arbitrary_action_labels_and_original_edges(self):
        problem = graph_tests.GraphProblem(
            {'S': {'launch': 'A'}, 'A': {'land': 'G'}}, 'S', 'G')
        for search, args in ((algorithms.breadth_first_graph_search, ()),
                             (algorithms.uniform_cost_search, ()),
                             (algorithms.depth_first_graph_search, ()),
                             (algorithms.astar_search, (lambda n: 0,))):
            goal, explored, elapsed_ms = search(problem, *args)
            self.assertEqual((goal.solution(), goal.depth, goal.path_cost), (['launch', 'land'], 2, 2))
            result = SolveResult(search.__name__, 0, goal, explored, elapsed_ms)
            self.assertEqual((result.solution_length, result.action_count), (2, 2))

    def test_bloxorz_initial_goal_and_unsolvable_keep_result_contract(self):
        won = self.session(tiles=['e'], start=(0, 0), goal=(0, 0))
        dead = self.session(tiles=['b      '] + ['       '] * 5 + ['      e'], start=(0, 0))
        for name in ('BFS', 'Uniform Cost Search', 'DFS', 'A*'):
            with self.subTest(algorithm=name):
                result = solve(won.level_number, name, measure_memory=False)
                self.assertEqual((result.solution_length, result.action_count, result.solution_cost), (0, 0, 0))
                self.assertEqual(result.goal_node.depth, 0)
                result = solve(dead.level_number, name, measure_memory=False)
                self.assertFalse(result.solved)
                self.assertIsNone(result.action_count)
                self.assertGreaterEqual(result.elapsed_ms, 0)


class ReplayMetricsTests(_RollingFixture, unittest.TestCase):
    """Complete primitive SWITCH paths, Node conversion and MOVES/ACTIONS/COST."""

    def test_bfs_minimizes_rolls_even_with_more_switches_and_more_actions(self):
        session = self.tradeoff()
        result = solve(session.level_number, 'BFS', measure_memory=False)
        # A legal 11-roll route never splits or switches, but is not roll-optimal.
        alternative = ['RIGHT', 'RIGHT', 'DOWN', 'DOWN', 'DOWN', 'DOWN',
                       'DOWN', 'LEFT', 'UP', 'LEFT', 'UP']
        self.walk(session, alternative)
        self.assertTrue(session.won)
        self.assertEqual((session.moves, session.action_count, session.cost), (11, 11, 11))
        session.reset()
        self.assertEqual(result.solution_length, 10)
        self.assertEqual(result.goal_node.solution().count('SWITCH'), 2)
        self.assertEqual((result.action_count, result.solution_cost), (12, 12))
        self.replay(session, result)

    def test_ucs_accounts_for_switch_fees_when_selecting_a_cheaper_path(self):
        session = self.tradeoff()
        bfs = solve(session.level_number, 'BFS', measure_memory=False)
        ucs = solve(session.level_number, 'Uniform Cost Search', measure_memory=False)
        self.assertEqual((ucs.solution_length, ucs.action_count, ucs.solution_cost), (10, 11, 11))
        self.assertEqual(ucs.goal_node.solution().count('SWITCH'), 1)
        self.assertLess(ucs.solution_cost, bfs.solution_cost)
        self.replay(session, ucs)

    def test_current_state_hint_preserves_the_needed_switch_and_spent_cost(self):
        session = self.tradeoff()
        original = session.problem.initial
        self.walk(session, ['RIGHT', 'RIGHT'])
        state, counters = session.state, (session.moves, session.action_count, session.cost)
        result = solve_problem(session.problem, 'Uniform Cost Search', initial=state, measure_memory=True)
        self.assertIs(session.problem.initial, original)
        self.assertEqual(result.goal_node.solution()[0], 'SWITCH')
        hint = session.request_hint()
        self.assertEqual(hint.state, result.solution_path()[1].state)
        self.assertEqual(hint.action, 'SWITCH')
        self.assertEqual(hint.state.position, state.position)
        self.assertNotEqual(hint.state.active, state.active)
        self.assertEqual((session.moves, session.action_count, session.cost), counters)
        self.assertIs(session.state, state)
        self.replay(session, result)
        session.reset()
        self.assertEqual((session.moves, session.action_count, session.cost), (0, 0, 0))

    def test_direct_searches_and_facade_share_the_model_without_extra_expansions(self):
        session = self.tradeoff()
        problem = session.problem
        runners = [('BFS', algorithms.breadth_first_graph_search, ()),
                   ('Uniform Cost Search', algorithms.uniform_cost_search, ()),
                   ('DFS', algorithms.depth_first_graph_search, ()),
                   ('A*', algorithms.astar_search, (problem.h1,))]
        for name, search, args in runners:
            with self.subTest(algorithm=name):
                goal, explored, ms = search(problem, *args)
                facade = solve_problem(problem, name)
                self.assertEqual(goal.solution(), facade.goal_node.solution())
                raw_goal, raw_explored, _ = search.__wrapped__(_RollProblem(problem), *args)
                self.assertEqual(goal.path_cost, raw_goal.path_cost)
                self.assertEqual([getattr(n, 'state', n) for n in explored],
                                 [getattr(n, 'state', n) for n in raw_explored])
                if name in ('BFS', 'Uniform Cost Search'):
                    self.assertEqual(explored[-1], goal)
                    self.assertEqual([node.state for node in explored].count(goal.state), 1)
                    for node in explored:
                        self.assertTrue(all(isinstance(a, str) for a in node.solution()))
                session.reset()
                self.replay(session, SolveResult(name, session.level_number, goal, explored, ms))

    def test_conversion_keeps_distinct_paths_to_the_same_state(self):
        session = self.session(targets=(1, 1, 5, 1))
        self.walk(session, ['RIGHT', 'RIGHT'])
        model, root = _RollProblem(session.problem), Node(session.state)
        returned = root.child_node(model, ('UP',)).child_node(model, ('DOWN',))
        self.assertEqual(root, returned)
        converter = _PrimitiveNodes(model)
        first, last = converter.convert(root), converter.convert(returned)
        self.assertIsNot(first, last)
        self.assertIs(last.path()[0], first)
        self.assertEqual((last.solution(), last.depth, last.path_cost), (['UP', 'DOWN'], 2, 2))

    def test_real_catalog_dfs_split_path_replays_every_primitive(self):
        with patch('engine.level.BASE_DIR', Path(__file__).resolve().parents[1]):
            session = GameSession(29)
            result = solve(29, 'DFS', measure_memory=False)
            self.assertIn('SWITCH', result.goal_node.solution())
            self.assertTrue(any(node.state.split for node in result.solution_path()))
            self.replay(session, result)


class SessionCostTests(unittest.TestCase):
    """Played cost accumulation, invalid actions, reset and non-spending previews."""

    def test_cost_starts_at_zero_and_reset_clears_it(self):
        session = GameSession(54)
        self.assertEqual((session.moves, session.cost), (0, 0))
        self.assertTrue(session.move('RIGHT'))
        self.assertEqual((session.moves, session.cost), (1, 3))
        session.reset()
        self.assertEqual((session.moves, session.cost), (0, 0))
        self.assertEqual(session.state, session.problem.initial)

    def test_moves_and_attempt_move_charge_the_shared_cost_once(self):
        session = fixture_session(((1, 3), (2, 3)))
        with patch.object(session.problem, 'path_cost', wraps=session.problem.path_cost) as cost:
            before = session.state
            self.assertTrue(session.move('RIGHT'))
            cost.assert_called_once_with(0, before, 'RIGHT', session.state)
            self.assertEqual(session.cost, 3)
            cost.reset_mock()
            before = session.state
            self.assertEqual(session.attempt_move('UP')[0], 'moved')
            cost.assert_called_once_with(3, before, 'UP', session.state)
        self.assertEqual((session.moves, session.cost), (2, 4))

    def test_switch_charges_one_and_ignores_stationary_fragile_cube(self):
        session = fixture_session(((1, 1),), split=True)
        for action in ('RIGHT', 'RIGHT'):
            self.assertTrue(session.move(action))
        self.assertTrue(session.is_split)
        self.assertEqual(session.cost, 4)
        before = session.state
        moves, actions = session.moves, session.action_count
        self.assertTrue(session.move('SWITCH'))
        self.assertEqual(session.cost, 5)
        self.assertEqual((session.moves, session.action_count), (moves, actions + 1))
        self.assertEqual(session.active, 1 - before.active)
        self.assertEqual(session.state.position, before.position)
        self.assertTrue(session.move('UP'))
        self.assertEqual((session.moves, session.action_count, session.cost), (3, 4, 6))

    def test_rejected_actions_do_not_charge_or_change_counters(self):
        session = fixture_session(((1, 3), (3, 3)))
        self.assertTrue(session.move('RIGHT'))
        before = session.state
        with patch.object(session.problem, 'path_cost', wraps=session.problem.path_cost) as cost:
            for action in ('RIGHT', 'SWITCH'):
                self.assertFalse(session.move(action))
            cost.assert_not_called()
        self.assertEqual((session.moves, session.cost), (1, 3))
        self.assertIs(session.state, before)

    def test_winning_move_charges_but_actions_after_win_do_not(self):
        session = GameSession(54)
        self.assertTrue(session.move('RIGHT'))
        self.assertTrue(session.move('RIGHT'))
        self.assertTrue(session.won)
        self.assertEqual((session.moves, session.cost), (2, 4))
        self.assertFalse(session.move('LEFT'))
        self.assertEqual((session.moves, session.cost), (2, 4))

    def test_hint_solve_and_memory_measurement_do_not_spend_play_cost(self):
        from ui3d.autoplay import solve_from
        session = GameSession(54)
        self.assertTrue(session.move('RIGHT'))
        before = (session.state, session.moves, session.cost)
        self.assertIsNotNone(session.request_hint())
        moves, result, error = solve_from(session, 'Uniform Cost Search')
        self.assertIsNone(error)
        self.assertEqual((moves, result.solution_cost), (['RIGHT'], 1))
        solve_problem(session.problem, 'BFS', initial=session.state, measure_memory=True)
        self.assertEqual((session.state, session.moves, session.cost), before)

    def test_set_state_keeps_play_cost_and_existing_move_count_options(self):
        session = GameSession(1)
        self.assertTrue(session.move('RIGHT'))
        other = session.problem.result(session.state, 'RIGHT')
        with patch.object(session.problem, 'path_cost', wraps=session.problem.path_cost) as cost:
            session.set_state(session.problem.initial, increment_moves=False)
            self.assertEqual((session.moves, session.cost), (1, 1))
            session.set_state(other)
            self.assertEqual((session.moves, session.cost), (2, 1))
            session.set_state(other)
            self.assertEqual((session.moves, session.cost), (2, 1))
            cost.assert_not_called()

    def test_new_level_and_new_tower_floor_start_at_zero(self):
        tower = Tower((54, 1))
        result = solve(54, 'BFS', measure_memory=False)
        for action in result.goal_node.solution():
            self.assertTrue(tower.session.move(action))
        self.assertEqual(tower.session.cost, 4)
        self.assertTrue(tower.descend())
        self.assertEqual((tower.session.moves, tower.session.cost), (0, 0))
        self.assertEqual(tower.total_moves, 2)
        self.assertEqual(GameSession(33).cost, 0)

    def test_level_33_bfs_and_ucs_replay_cost_matches_solution_cost(self):
        for algorithm, length, total in (('BFS', 46, 68), ('Uniform Cost Search', 49, 63)):
            with self.subTest(algorithm=algorithm):
                result = solve(33, algorithm, measure_memory=False)
                self.assertEqual((result.solution_length, result.solution_cost), (length, total))
                session = GameSession(33)
                for action in result.goal_node.solution():
                    self.assertTrue(session.move(action))
                self.assertTrue(session.won)
                self.assertEqual((session.moves, session.cost), (length, total))


class ExploredContractTests(unittest.TestCase):
    """Goal inclusion without successors, and legitimate A* state reopening."""

    def run_search(self, name, problem, h=None):
        functions = {'BFS': algorithms.breadth_first_graph_search,
                     'DFS': algorithms.depth_first_graph_search,
                     'UCS': algorithms.uniform_cost_search, 'A*': algorithms.astar_search}
        return functions[name](problem, h or (lambda node: 0)) if name == 'A*' else functions[name](problem)

    def states(self, explored):
        return [getattr(item, 'state', item) for item in explored]

    def test_initial_goal_is_recorded_once_and_has_no_successors(self):
        for name in ('BFS', 'DFS', 'UCS', 'A*'):
            with self.subTest(algorithm=name):
                problem = graphs.WeightedGraphProblem({'G': {'must_not_run': ('X', 1)}}, initial='G')
                goal, explored, _ = self.run_search(name, problem)
                self.assertEqual(self.states(explored), ['G'])
                self.assertEqual(problem.expanded_states, [])
                self.assertEqual(problem.goal_checks, ['G'])
                self.assertEqual(goal.solution(), [])

    def test_astar_records_a_reopened_state_and_skips_the_stale_child(self):
        problem = graphs.WeightedGraphProblem({
            'S': {'to_a': ('A', 3), 'to_b': ('B', 1)}, 'A': {'to_c': ('C', 1)},
            'B': {'improve_a': ('A', 1)}, 'C': {'finish': ('G', 20)}})
        # Admissible but inconsistent on B -> A, so A is legitimately reopened.
        goal, explored, _ = self.run_search('A*', problem, lambda n: 3 if n.state == 'B' else 0)
        self.assertEqual(self.states(explored), ['S', 'A', 'B', 'A', 'C', 'G'])
        self.assertEqual(problem.goal_checks, ['S', 'A', 'B', 'A', 'C', 'G'])
        self.assertEqual(problem.expanded_states, ['S', 'A', 'B', 'A', 'C'])
        self.assertEqual(goal.path_cost, 23)


class BridgeSwitchIntegrationTests(_GameAssertions, unittest.TestCase):
    """Bridge closure falls and moving/stationary switch effects during merge."""

    def assert_falling_action(self, problem, prefix, action):
        session = session_for(problem)
        self.walk(session, prefix)
        before = session.state
        counters = session.moves, session.action_count, session.cost
        self.assertIsNone(problem.result(before, action))
        self.assertNotIn(action, problem.actions(before))
        self.assertNotIn(action, [node.action for node in Node(before).expand(problem)])
        status, _, after = session.attempt_move(action)
        self.assertEqual(status, 'fell')
        self.assertIs(after, before)
        self.assertEqual((session.moves, session.action_count, session.cost), counters)
        for algorithm in ('BFS', 'Uniform Cost Search'):
            result = solve_problem(problem, algorithm, initial=before)
            self.assertTrue(result.solved)
            for node in result.explored + result.solution_path():
                self.assertTrue(all(problem._floor(cell, node.state.bridges)
                                    for cell in session.block_cells(node.state)))

    def test_toggle_closing_bridge_under_landing_block_falls(self):
        self.assert_falling_action(switch_problem(), ['RIGHT'], 'UP')

    def test_toggle_closing_bridge_under_stationary_cube_falls(self):
        problem = switch_problem((1, 1, 4, 1), stationary_bridge=True)
        self.assert_falling_action(problem, ['RIGHT', 'RIGHT', 'SWITCH'], 'LEFT')

    def test_merging_does_not_retoggle_stationary_soft_switch(self):
        session = session_for(switch_problem((1, 2, 4, 1)))
        self.walk(session, ['RIGHT', 'RIGHT', 'DOWN'])
        self.assertEqual(session.state.bridges, (1,))   # cube really entered the soft switch
        self.walk(session, ['SWITCH', 'LEFT', 'LEFT'])
        self.assertFalse(session.is_split)
        self.assertEqual(session.state.position, [1, 1, 2, 1])
        self.assertEqual(session.state.bridges, (1,))   # no second activation just for merging
        self.walk(session, ['UP', 'DOWN'])
        self.assertEqual(session.state.bridges, (0,))

    def test_moving_cube_switch_activates_while_stationary_one_does_not(self):
        for kind, expected in (('s', (1, 1)), ('h', (1, 0))):
            with self.subTest(destination=kind):
                session = session_for(switch_problem((1, 2, 4, 1), landing_switch=kind))
                self.walk(session, ['RIGHT', 'RIGHT', 'DOWN', 'SWITCH', 'LEFT'])
                self.assertEqual(session.state.bridges, (1, 0))
                self.assertTrue(session.is_split)
                self.walk(session, ['LEFT'])
                self.assertFalse(session.is_split)
                self.assertEqual(session.state.bridges, expected)


if __name__ == '__main__':
    unittest.main()
