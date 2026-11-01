"""Benchmark script for Bloxorz Solvers (BFS, DFS, UCS, A*).

Runs a fixed test set of 18 stages grouped by difficulty,
measuring Search Time (ms), Peak Memory (KB), Expanded Nodes,
Solution Moves, and Solution Cost.
"""
import sys
from engine.solver import solve

# Fixed test set grouped by increasing difficulty
TEST_LEVELS = {
    'A_Simple': [1, 10, 15, 20, 21],
    'B_Fragile': [24, 33, 54],
    'C_Switches_Bridges': [22, 25, 27, 34, 55],
    'D_Combined': [29, 30, 35, 40, 51]
}

ALGORITHMS = ['BFS', 'DFS', 'Uniform Cost Search', 'A*']


def run_benchmark():
    print("=" * 85)
    print("BLOXORZ EXPERIMENTAL BENCHMARK - 4 SEARCH ALGORITHMS")
    print("=" * 85)
    header = f"{'Group':<20} | {'Lvl':<3} | {'Algorithm':<20} | {'Time (ms)':<10} | {'RAM (KB)':<10} | {'Expanded':<8} | {'Moves':<5} | {'Cost':<5}"
    print(header)
    print("-" * 85)

    for group, levels in TEST_LEVELS.items():
        for lvl in levels:
            for algo in ALGORITHMS:
                try:
                    res = solve(lvl, algo, measure_memory=True)
                    t_ms = f"{res.elapsed_ms:.2f}"
                    mem_kb = f"{res.peak_memory_kb:.1f}" if res.peak_memory_kb is not None else "N/A"
                    exp = str(res.expanded)
                    moves = str(res.solution_length) if res.solved else "N/A"
                    cost = str(res.solution_cost) if res.solved else "N/A"
                    print(f"{group:<20} | {lvl:<3} | {algo:<20} | {t_ms:<10} | {mem_kb:<10} | {exp:<8} | {moves:<5} | {cost:<5}")
                except Exception as e:
                    print(f"{group:<20} | {lvl:<3} | {algo:<20} | ERROR: {e}")
                sys.stdout.flush()
        print("-" * 85)


if __name__ == '__main__':
    run_benchmark()
