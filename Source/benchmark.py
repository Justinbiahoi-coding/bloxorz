"""Benchmark script for Bloxorz Solvers (BFS, DFS, UCS, A*).

Runs a fixed test set of 18 stages grouped by difficulty,
measuring Search Time (ms), Peak Memory (KB), Expanded Nodes,
Solution Moves, and Solution Cost.
Automatically saves results to benchmark_results.json for plotting.
"""
import json
import os
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

    all_results = []

    for group, levels in TEST_LEVELS.items():
        for lvl in levels:
            for algo in ALGORITHMS:
                try:
                    res = solve(lvl, algo, measure_memory=True)
                    t_ms = round(res.elapsed_ms, 2)
                    mem_kb = round(res.peak_memory_kb, 1) if res.peak_memory_kb is not None else None
                    exp = res.expanded
                    moves = res.solution_length if res.solved else None
                    cost = res.solution_cost if res.solved else None
                    
                    record = {
                        'group': group,
                        'level': lvl,
                        'algorithm': algo,
                        'time_ms': t_ms,
                        'peak_memory_kb': mem_kb,
                        'expanded': exp,
                        'moves': moves,
                        'cost': cost
                    }
                    all_results.append(record)

                    mem_str = f"{mem_kb:.1f}" if mem_kb is not None else "N/A"
                    moves_str = str(moves) if moves is not None else "N/A"
                    cost_str = str(cost) if cost is not None else "N/A"
                    print(f"{group:<20} | {lvl:<3} | {algo:<20} | {t_ms:<10.2f} | {mem_str:<10} | {exp:<8} | {moves_str:<5} | {cost_str:<5}")
                except Exception as e:
                    print(f"{group:<20} | {lvl:<3} | {algo:<20} | ERROR: {e}")
                sys.stdout.flush()
        print("-" * 85)

    # Save to JSON
    json_path = os.path.join(os.path.dirname(__file__), 'benchmark_results.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[DONE] Benchmark completed! Results saved to: {json_path}")


if __name__ == '__main__':
    run_benchmark()
