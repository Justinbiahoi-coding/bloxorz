"""Check the project's BFS/UCS and replay on every level; standard library only.

Run: python -B Source/check_bfs_levels.py
UCS: python -B Source/check_bfs_levels.py --algorithm UCS
Compare: python -B Source/check_bfs_levels.py --algorithm both
Each child has 10 seconds for startup, search, and replay combined. The
search_ms column comes from the solver, not from the child process lifetime.
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
ALGORITHMS = {'BFS': 'BFS', 'UCS': 'Uniform Cost Search'}


def check_level(level_id, algorithm='BFS'):
    """Executed in a child; always label results with the filename's ID."""
    row = {'id': level_id, 'algorithm': algorithm, 'actions': None, 'cost': None,
           'expanded': None, 'search_ms': None}
    phase = 'search'
    context = {}
    try:
        from engine import GameSession, solve

        result = solve(level_id, ALGORITHMS[algorithm])
        row.update(expanded=len(result.explored), search_ms=result.elapsed_ms)
        if result.goal_node is None:
            row['status'] = 'UNSOLVABLE'
            return row

        phase = 'replay'
        actions = result.goal_node.solution()
        row.update(actions=len(actions), cost=result.goal_node.path_cost)
        session = GameSession(level_id)
        for index, action in enumerate(actions, start=1):
            context = {'action_index': index, 'action': action,
                       'state_before': dict(vars(session.state))}
            if not session.move(action):
                raise RuntimeError('GameSession.move rejected the action')
        context['final_state'] = dict(vars(session.state))
        if not session.won:
            raise RuntimeError('Replay finished without reaching the goal')
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

    print('{}{:>3}  {:<12}  {:>7}  {:>8}  {:>9}  {:>12}'.format(
        prefix, row['id'], row['status'], cell('actions'), cell('cost'),
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
    header = ' ID  STATUS        ACTIONS      COST   EXPANDED     SEARCH_MS'
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
    """Compare step counts under the game's current unit step costs."""
    bfs_by_id = {row['id']: row for row in bfs_results}
    mismatches = []
    inconclusive = []
    matches = 0
    print('\nBFS/UCS ACTION COUNTS (game currently uses cost=1 per action)', flush=True)
    print(' ID      BFS      UCS  RESULT', flush=True)
    for ucs in ucs_results:
        level_id = ucs['id']
        bfs = bfs_by_id[level_id]
        if bfs['status'] != 'SOLVED' or ucs['status'] != 'SOLVED':
            outcome = 'INCONCLUSIVE'
            inconclusive.append(level_id)
        elif bfs['actions'] != ucs['actions']:
            outcome = 'MISMATCH'
            mismatches.append(level_id)
        else:
            outcome = 'MATCH'
            matches += 1
        print('{:>3}  {:>7}  {:>7}  {}'.format(
            level_id, str(bfs.get('actions', '-')), str(ucs.get('actions', '-')),
            outcome), flush=True)
    print('COMPARISON: matches={}, mismatch_ids={}, inconclusive_ids={}'.format(
        matches, mismatches, inconclusive), flush=True)
    return not mismatches and not inconclusive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--algorithm', choices=('BFS', 'UCS', 'both'), default='BFS',
                        help='Default BFS preserves the original command; both compares step counts.')
    parser.add_argument('--worker', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        if args.algorithm == 'both':
            parser.error('A worker must run exactly one algorithm')
        print(json.dumps(check_level(args.worker, args.algorithm), ensure_ascii=True))
        return 0

    from engine import FLOORS

    # This is the same filename-based list used by the Algorithms selector.
    level_ids = sorted(int(path.stem)
                       for path in (SOURCE_DIR / 'levels').glob('*.json'))
    if not level_ids:
        parser.error('No level JSON files found')
    algorithms = ('BFS', 'UCS') if args.algorithm == 'both' else (args.algorithm,)
    suites = {name: run_suite(level_ids, name, FLOORS) for name in algorithms}
    passed = all(row['status'] == 'SOLVED'
                 for results in suites.values() for row in results)
    if args.algorithm == 'both':
        passed = compare_suites(suites['BFS'], suites['UCS']) and passed
    return 0 if passed and not set(FLOORS) - set(level_ids) else 1


if __name__ == '__main__':
    sys.exit(main())
