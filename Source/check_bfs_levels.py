"""Check real BFS/UCS/A* searches and replay on every level; standard library only.

Run: python -B Source/check_bfs_levels.py
UCS: python -B Source/check_bfs_levels.py --algorithm UCS
Compare: python -B Source/check_bfs_levels.py --algorithm both
All three: python -B Source/check_bfs_levels.py --algorithm all
Each child has 10 seconds for startup, search, and replay combined. The
search_ms column comes from the solver, not from the child process lifetime.
ACTIONS includes SWITCH; MOVES excludes SWITCH. COST uses the full action count.
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback


SOURCE_DIR = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 10
STATUSES = ('SOLVED', 'UNSOLVABLE', 'TIMEOUT', 'SEARCH_ERROR', 'REPLAY_ERROR')
ALGORITHMS = {'BFS': 'BFS', 'UCS': 'Uniform Cost Search', 'A*': 'A*'}


def fragile_landing(level, before, action, after):
    """Independent replay audit: calculate a moved cube's destination directly.

    This intentionally does not call Bloxorz.path_cost. The game cost filters
    the stationary cube out of the final cells; here the old active cube plus
    the action's offset identifies the landing, even after a merge.
    """
    if action == 'SWITCH':
        return False
    if before.split:
        dx, dy = {'UP': (0, 1), 'DOWN': (0, -1), 'LEFT': (-1, 0), 'RIGHT': (1, 0)}[action]
        index = 2 * before.active
        cells = [(before.position[index] + dx, before.position[index + 1] + dy)]
    else:
        # Whole block: both final cells count, including split/teleport targets.
        cells = zip(after.position[::2], after.position[1::2])
    return any(level.kinds.get(cell) == 'f' for cell in cells)


def check_level(level_id, algorithm='BFS'):
    """Executed in a child; always label results with the filename's ID."""
    row = {'id': level_id, 'algorithm': algorithm, 'actions': None, 'moves': None, 'switches': None, 'cost': None,
           'surcharged_actions': None, 'expanded': None, 'search_ms': None}
    phase = 'search'
    context = {}
    try:
        from engine import GameSession, solve

        # This is a correctness audit; do not repeat the search to measure memory.
        result = solve(level_id, ALGORITHMS[algorithm], measure_memory=False)
        row.update(expanded=len(result.explored), search_ms=result.elapsed_ms)
        if result.solved:
            considered = [getattr(item, 'state', item) for item in result.explored]
            if (not considered or considered[-1] != result.goal_node.state
                    or considered.count(result.goal_node.state) != 1):
                raise RuntimeError('Explored must end with the goal exactly once')
        if result.goal_node is None:
            row['status'] = 'UNSOLVABLE'
            return row

        phase = 'replay'
        actions = result.goal_node.solution()
        row.update(actions=len(actions), moves=result.solution_length, switches=actions.count('SWITCH'),
                   cost=result.goal_node.path_cost, solution=actions)
        session = GameSession(level_id)
        path = result.solution_path()
        if len(path) != len(actions) + 1 or path[0].state != session.state or path[0].path_cost != 0:
            raise RuntimeError('Invalid primitive solution root/path length')
        surcharged = 0
        for index, action in enumerate(actions, start=1):
            before = session.state
            context = {'action_index': index, 'action': action,
                       'state_before': dict(vars(before))}
            if action not in session.actions():
                raise RuntimeError('Solution contains an illegal action')
            if not session.move(action):
                raise RuntimeError('GameSession.move rejected the action')
            node = path[index]
            if node.path_cost != session.cost:
                raise RuntimeError('Cost mismatch at action {}: node={}, session={}'.format(
                    index, node.path_cost, session.cost))
            if (node.action != action or node.state != session.state or node.depth != index
                    or node.parent is not path[index - 1]):
                raise RuntimeError('Public Node path does not match primitive replay')
            surcharged += fragile_landing(session.level, before, action, session.state)
        context['final_state'] = dict(vars(session.state))
        if not session.won:
            raise RuntimeError('Replay finished without reaching the goal')
        replay_moves = sum(action != 'SWITCH' for action in actions)
        if (session.action_count != len(actions) or result.action_count != len(actions)
                or session.moves != replay_moves or row['moves'] != replay_moves):
            raise RuntimeError('Replay action/MOVES counts do not match the solution')
        replay_cost = len(actions) + 2 * surcharged
        row.update(surcharged_actions=surcharged, replay_cost=replay_cost)
        if replay_cost != row['cost'] or session.cost != row['cost']:
            raise RuntimeError('Cost mismatch: solver={}, independent replay={}'.format(
                row['cost'], replay_cost))
        row['status'] = 'SOLVED'
    except Exception as exc:
        row.update(status='SEARCH_ERROR' if phase == 'search' else 'REPLAY_ERROR',
                   phase=phase, context=context,
                   error='{}: {}'.format(type(exc).__name__, exc),
                   traceback=traceback.format_exc())
    return row


def run_child(level_id, algorithm='BFS'):
    command = [sys.executable, '-B', '-u', str(Path(__file__).resolve()),
               '--worker', str(level_id), '--algorithm', algorithm]
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with subprocess.Popen(command, cwd=str(SOURCE_DIR), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding='utf-8', errors='replace',
                          creationflags=flags) as process:
        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            # Wait for termination before returning and starting another level.
            stdout, stderr = process.communicate()
            return {'id': level_id, 'algorithm': algorithm, 'status': 'TIMEOUT',
                    'error': 'Exceeded 10 seconds; child killed and reaped.',
                    'stdout': stdout, 'stderr': stderr}
        except BaseException:
            process.kill()
            process.communicate()
            raise

    try:
        row = json.loads(stdout)
        if process.returncode != 0:
            raise ValueError('Worker exited with code {}'.format(process.returncode))
        if (row['id'] != level_id or row['algorithm'] != algorithm
                or row['status'] not in STATUSES):
            raise ValueError('Invalid worker result')
        return row
    except (ValueError, KeyError, TypeError) as exc:
        return {'id': level_id, 'algorithm': algorithm, 'status': 'SEARCH_ERROR',
                'error': 'Worker/protocol error: {}'.format(exc),
                'stdout': stdout, 'stderr': stderr}


def print_row(row, prefix=''):
    def cell(key):
        value = row.get(key)
        if value is None:
            return '-'
        return '{:.3f}'.format(value) if key == 'search_ms' else str(value)

    print('{}{:>3}  {:<12}  {:>7}  {:>6}  {:>6}  {:>8}  {:>8}  {:>9}  {:>12}'.format(
        prefix, row['id'], row['status'], cell('actions'), cell('moves'), cell('switches'), cell('surcharged_actions'), cell('cost'),
        cell('expanded'), cell('search_ms')), flush=True)


def print_details(row):
    for key in ('error', 'context', 'traceback', 'stdout', 'stderr'):
        if row.get(key):
            value = row[key]
            if isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=True)
            print('  {}: {}'.format(key, value), flush=True)


def run_suite(level_ids, algorithm, floors):
    print('\nChecking {} levels; timeout={}s per child; {} from level start.'.format(
        len(level_ids), TIMEOUT_SECONDS, algorithm), flush=True)
    print('IDs: {}'.format(', '.join(map(str, level_ids))), flush=True)
    print('search_ms is reported by the solver; SOLVED requires successful replay.', flush=True)
    header = ' ID  STATUS        ACTIONS   MOVES  SWITCH  FRAGILE      COST   EXPANDED     SEARCH_MS'
    results = []
    print(header, flush=True)
    for number, level_id in enumerate(level_ids, start=1):
        row = run_child(level_id, algorithm)
        results.append(row)
        print_row(row, '[{}/{}] '.format(number, len(level_ids)))
        if row['status'] in ('SEARCH_ERROR', 'REPLAY_ERROR'):
            print_details(row)

    print('\nALL LEVELS\n' + header, flush=True)
    for row in results:
        print_row(row)
    counts = Counter(row['status'] for row in results)
    print('\nTOTALS: ' + ', '.join('{}={}'.format(status, counts[status])
                                  for status in STATUSES), flush=True)
    by_id = {row['id']: row for row in results}
    print('\nTOWER (default floor order)\n' + header, flush=True)
    for level_id in floors:
        if level_id in by_id:
            print_row(by_id[level_id])
        else:
            print('Missing Tower level file: {}'.format(level_id), flush=True)
    review = [row['id'] for row in results if row['status'] != 'SOLVED']
    print('\nREVIEW IDs: {}'.format(review), flush=True)
    print('TIMEOUT is inconclusive; UNSOLVABLE means the solver returned None.', flush=True)
    return results


def compare_suites(bfs_results, ucs_results):
    """UCS must cost no more than BFS; the two action counts may differ."""
    bfs_by_id = {row['id']: row for row in bfs_results}
    violations = []
    cheaper = []
    more_actions = []
    inconclusive = []
    equal = 0
    print('\nBFS/UCS: compare penalized cost, not action-count equality', flush=True)
    print(' ID  BFS_ACT UCS_ACT  BFS_MOVES UCS_MOVES  BFS_COST UCS_COST  RESULT', flush=True)
    for ucs in ucs_results:
        level_id = ucs['id']
        bfs = bfs_by_id[level_id]
        if bfs['status'] != 'SOLVED' or ucs['status'] != 'SOLVED':
            outcome = 'INCONCLUSIVE'
            inconclusive.append(level_id)
        elif bfs['moves'] > ucs['moves']:
            outcome = 'BFS_MORE_MOVES'
            violations.append(level_id)
        elif ucs['cost'] > bfs['cost']:
            outcome = 'UCS_MORE_EXPENSIVE'
            violations.append(level_id)
        elif ucs['cost'] < bfs['cost']:
            cheaper.append(level_id)
            if ucs['actions'] > bfs['actions']:
                more_actions.append(level_id)
                outcome = 'UCS_CHEAPER_MORE_ACTIONS'
            elif ucs['actions'] == bfs['actions']:
                outcome = 'UCS_CHEAPER_SAME_ACTIONS'
            else:
                outcome = 'UCS_CHEAPER_FEWER_ACTIONS'
        else:
            outcome = 'EQUAL_COST'
            equal += 1
        print('{:>3}  {:>7} {:>7}  {:>9} {:>9}  {:>8} {:>8}  {}'.format(
            level_id, str(bfs.get('actions', '-')), str(ucs.get('actions', '-')),
            str(bfs.get('moves', '-')), str(ucs.get('moves', '-')),
            str(bfs.get('cost', '-')), str(ucs.get('cost', '-')), outcome), flush=True)
    print('COMPARISON: equal={}, ucs_cheaper_ids={}, more_action_ids={}, '
          'violation_ids={}, inconclusive_ids={}'.format(
              equal, cheaper, more_actions, violations, inconclusive), flush=True)
    return not violations and not inconclusive


def compare_astar(ucs_results, astar_results):
    """Report cost disagreements and independently rerun both real solvers."""
    ucs_by_id = {row['id']: row for row in ucs_results}
    differences = []
    inconclusive = []
    equal = 0
    print('\nA*/UCS COST COMPARISON (A* uses the relaxed-distance h1)', flush=True)
    for astar in astar_results:
        level_id = astar['id']
        ucs = ucs_by_id[level_id]
        if astar['status'] != 'SOLVED' or ucs['status'] != 'SOLVED':
            inconclusive.append(level_id)
        elif astar['cost'] == ucs['cost']:
            equal += 1
        else:
            differences.append(level_id)
            relation = 'HIGHER' if astar['cost'] > ucs['cost'] else 'LOWER'
            print('Level {}: A* {} than UCS; A* actions/moves/cost={}/{}/{}, UCS={}/{}/{}'.format(
                level_id, relation, astar['actions'], astar['moves'], astar['cost'],
                ucs['actions'], ucs['moves'], ucs['cost']), flush=True)
            for original in (ucs, astar):
                print('  Initial result: ' + json.dumps(original, ensure_ascii=True), flush=True)
                rerun = run_child(level_id, original['algorithm'])
                print('  Confirmation: ' + json.dumps(rerun, ensure_ascii=True), flush=True)
    print('A*/UCS: equal={}, different_ids={}, inconclusive_ids={}'.format(
        equal, differences, inconclusive), flush=True)
    return not differences and not inconclusive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--algorithm', choices=tuple(ALGORITHMS) + ('both', 'all'), default='BFS',
                        help='Default BFS; both compares BFS/UCS costs; all also checks A* with h1.')
    parser.add_argument('--worker', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        if args.algorithm not in ALGORITHMS:
            parser.error('A worker must run exactly one algorithm')
        print(json.dumps(check_level(args.worker, args.algorithm), ensure_ascii=True))
        return 0

    from engine import FLOORS

    # This is the same filename-based list used by the Algorithms selector.
    level_ids = sorted(int(path.stem)
                       for path in (SOURCE_DIR / 'levels').glob('*.json'))
    if not level_ids:
        parser.error('No level JSON files found')
    if args.algorithm == 'all':
        algorithms = tuple(ALGORITHMS)
    else:
        algorithms = ('BFS', 'UCS') if args.algorithm == 'both' else (args.algorithm,)
    suites = {name: run_suite(level_ids, name, FLOORS) for name in algorithms}
    passed = all(row['status'] == 'SOLVED'
                 for results in suites.values() for row in results)
    if args.algorithm in ('both', 'all'):
        passed = compare_suites(suites['BFS'], suites['UCS']) and passed
    if args.algorithm == 'all':
        passed = compare_astar(suites['UCS'], suites['A*']) and passed
    return 0 if passed and not set(FLOORS) - set(level_ids) else 1


if __name__ == '__main__':
    sys.exit(main())
