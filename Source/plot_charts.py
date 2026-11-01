"""Generate professional academic comparison charts for Bloxorz Solvers benchmark.
Reads dynamic data from benchmark_results.json if available, or falls back to
verified baseline benchmark data.
Saves high-resolution PNG charts ready to be inserted into the final report.
"""
import json
import os
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = os.path.dirname(__file__)
CHARTS_DIR = os.path.join(BASE_DIR, 'charts')
JSON_PATH = os.path.join(BASE_DIR, 'benchmark_results.json')
os.makedirs(CHARTS_DIR, exist_ok=True)

# Set global styling
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

# Color palette for 4 algorithms
COLORS = {
    'BFS': '#2b5c8f',       # Steel Blue
    'DFS': '#d95f02',       # Dark Orange
    'UCS': '#7570b3',       # Purple
    'A*': '#1b9e77'         # Emerald Green
}

# Load benchmark data if available
RESULTS_MAP = {}
if os.path.exists(JSON_PATH):
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                # Key: (level, algo)
                RESULTS_MAP[(item['level'], item['algorithm'])] = item
        print(f"[INFO] Loaded dynamic benchmark data from: {JSON_PATH}")
    except Exception as e:
        print(f"[WARNING] Could not parse {JSON_PATH}: {e}. Using baseline data.")


def get_metric(level, algo, metric, fallback):
    if (level, algo) in RESULTS_MAP and RESULTS_MAP[(level, algo)].get(metric) is not None:
        return RESULTS_MAP[(level, algo)][metric]
    return fallback


# -------------------------------------------------------------
# 1. CHART 1: Solution Length (Moves) Comparison (Selected Levels)
# -------------------------------------------------------------
def plot_solution_moves():
    level_nums = [1, 21, 24, 22, 29, 30]
    level_labels = ['L1\n(Simple)', 'L21\n(Simple)', 'L24\n(Fragile)', 'L22\n(Bridge)', 'L29\n(Split)', 'L30\n(Combined)']

    fallbacks = {
        'BFS': [4, 7, 28, 17, 24, 57],
        'DFS': [4, 43, 36, 120, 1298, 2639],
        'UCS': [4, 7, 28, 17, 24, 57],
        'A*': [4, 7, 28, 17, 24, 57]
    }

    moves_bfs = [get_metric(lvl, 'BFS', 'moves', fb) for lvl, fb in zip(level_nums, fallbacks['BFS'])]
    moves_dfs = [get_metric(lvl, 'DFS', 'moves', fb) for lvl, fb in zip(level_nums, fallbacks['DFS'])]
    moves_ucs = [get_metric(lvl, 'Uniform Cost Search', 'moves', fb) for lvl, fb in zip(level_nums, fallbacks['UCS'])]
    moves_astar = [get_metric(lvl, 'A*', 'moves', fb) for lvl, fb in zip(level_nums, fallbacks['A*'])]

    x = np.arange(len(level_labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    
    ax.bar(x - 1.5*width, moves_bfs, width, label='BFS', color=COLORS['BFS'])
    ax.bar(x - 0.5*width, moves_dfs, width, label='DFS', color=COLORS['DFS'])
    ax.bar(x + 0.5*width, moves_ucs, width, label='UCS', color=COLORS['UCS'])
    ax.bar(x + 1.5*width, moves_astar, width, label='A*', color=COLORS['A*'])

    ax.set_ylabel('Solution Length (Number of Moves) - Log Scale', fontsize=11, fontweight='bold')
    ax.set_title('Figure 1: Solution Length (Moves) Comparison Across Representative Stages', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(level_labels, fontsize=10)
    ax.set_yscale('log')
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # Annotate exact numbers for high DFS bars
    ax.annotate(f'{moves_dfs[4]:,}', xy=(4 - 0.5*width, moves_dfs[4]), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['DFS'])
    ax.annotate(f'{moves_dfs[5]:,}', xy=(5 - 0.5*width, moves_dfs[5]), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['DFS'])
    ax.annotate(f'{moves_astar[4]}', xy=(4 + 1.5*width, moves_astar[4]), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['A*'])
    ax.annotate(f'{moves_astar[5]}', xy=(5 + 1.5*width, moves_astar[5]), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['A*'])

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, 'chart1_solution_moves.png')
    plt.savefig(path)
    plt.close()
    print(f'Saved: {path}')


# -------------------------------------------------------------
# 2. CHART 2: Peak Memory Usage (Group D - Complex Combined Stages)
# -------------------------------------------------------------
def plot_memory_group_d():
    level_nums = [29, 30, 35, 40, 51]
    levels = ['Level 29', 'Level 30', 'Level 35', 'Level 40', 'Level 51']
    
    fallbacks = {
        'BFS': [1315.5, 13791.5, 9936.1, 9435.3, 872.3],
        'DFS': [2172.7, 5544.1, 1318.2, 8089.4, 236.7],
        'UCS': [1294.3, 13597.6, 9701.5, 9761.2, 850.3],
        'A*': [401.9, 3601.9, 3025.2, 3177.9, 277.9]
    }

    mem_bfs = [get_metric(lvl, 'BFS', 'peak_memory_kb', fb) for lvl, fb in zip(level_nums, fallbacks['BFS'])]
    mem_dfs = [get_metric(lvl, 'DFS', 'peak_memory_kb', fb) for lvl, fb in zip(level_nums, fallbacks['DFS'])]
    mem_ucs = [get_metric(lvl, 'Uniform Cost Search', 'peak_memory_kb', fb) for lvl, fb in zip(level_nums, fallbacks['UCS'])]
    mem_astar = [get_metric(lvl, 'A*', 'peak_memory_kb', fb) for lvl, fb in zip(level_nums, fallbacks['A*'])]

    x = np.arange(len(levels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)

    ax.bar(x - 1.5*width, mem_bfs, width, label='BFS', color=COLORS['BFS'])
    ax.bar(x - 0.5*width, mem_dfs, width, label='DFS', color=COLORS['DFS'])
    ax.bar(x + 0.5*width, mem_ucs, width, label='UCS', color=COLORS['UCS'])
    ax.bar(x + 1.5*width, mem_astar, width, label='A*', color=COLORS['A*'])

    ax.set_ylabel('Peak Memory (KB)', fontsize=11, fontweight='bold')
    ax.set_title('Figure 2: Peak Memory Usage on Complex Stages (Group D - Split & Bridges)', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(levels, fontsize=10)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # Highlight A* memory savings on Level 30
    saving_mb = (mem_bfs[1] - mem_astar[1]) / 1024
    ax.annotate(f'A* saves ~{saving_mb:.1f} MB RAM!\n({mem_astar[1]/1024:.1f} MB vs {mem_bfs[1]/1024:.1f} MB)', 
                xy=(1 + 1.5*width, mem_astar[1]), 
                xytext=(1.2, 8500),
                arrowprops=dict(arrowstyle="->", color='#1b9e77', lw=1.5),
                fontsize=8.5, fontweight='bold', color='#1b9e77',
                bbox=dict(boxstyle="round,pad=0.3", fc="#e5f5f0", ec="#1b9e77", lw=1))

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, 'chart2_peak_memory_group_d.png')
    plt.savefig(path)
    plt.close()
    print(f'Saved: {path}')


# -------------------------------------------------------------
# 3. CHART 3: Trade-off Case Study at Level 33 (Moves vs Cost)
# -------------------------------------------------------------
def plot_tradeoff_level33():
    algos = ['BFS', 'DFS', 'UCS', 'A*']
    algo_keys = ['BFS', 'DFS', 'Uniform Cost Search', 'A*']
    
    fb_moves = [46, 65, 49, 49]
    fb_costs = [68, 95, 63, 63]

    moves = [get_metric(33, k, 'moves', fb) for k, fb in zip(algo_keys, fb_moves)]
    costs = [get_metric(33, k, 'cost', fb) for k, fb in zip(algo_keys, fb_costs)]

    x = np.arange(len(algos))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    rects1 = ax.bar(x - width/2, moves, width, label='Moves (Path Length)', color='#3182bd')
    rects2 = ax.bar(x + width/2, costs, width, label='Path Cost (With Fragile Surcharge)', color='#de2d26')

    ax.set_ylabel('Units', fontsize=11, fontweight='bold')
    ax.set_title('Figure 3: Moves vs Path Cost at Level 33 (Fragile Tiles Penalty)', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(algos, fontsize=11, fontweight='bold')
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # Add values on top of bars
    for r in rects1:
        h = r.get_height()
        ax.annotate(f'{int(h)}', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')
    for r in rects2:
        h = r.get_height()
        ax.annotate(f'{int(h)}', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')

    diff = int(costs[0] - costs[2])
    ax.text(0.5, 0.85, f'BFS minimizes Moves ({moves[0]} steps)\nUCS & A* minimize Cost ({costs[2]} cost vs {costs[0]})', 
            transform=ax.transAxes, ha='center', fontsize=9,
            bbox=dict(boxstyle="round,pad=0.4", fc="#fff7bc", ec="#d95f0e", lw=1))

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, 'chart3_tradeoff_level33.png')
    plt.savefig(path)
    plt.close()
    print(f'Saved: {path}')


# -------------------------------------------------------------
# 4. CHART 4: Average Expanded Nodes by Difficulty Group
# -------------------------------------------------------------
def plot_avg_expanded():
    groups = ['Group A\n(Simple)', 'Group B\n(Fragile)', 'Group C\n(Bridges)', 'Group D\n(Combined)']
    
    # Calculate dynamically if results map exists
    group_levels = {
        'A': [1, 10, 15, 20, 21],
        'B': [24, 33, 54],
        'C': [22, 25, 27, 34, 55],
        'D': [29, 30, 35, 40, 51]
    }
    
    fallbacks = {
        'BFS': [65.8, 69.3, 249.2, 5953.4],
        'DFS': [35.0, 64.7, 224.0, 2674.4],
        'UCS': [65.8, 69.7, 249.2, 5865.0],
        'A*': [47.6, 68.0, 212.2, 4786.0]
    }

    avg_bfs = []
    avg_dfs = []
    avg_ucs = []
    avg_astar = []

    for idx, (g, lvls) in enumerate(group_levels.items()):
        if RESULTS_MAP:
            avg_bfs.append(np.mean([get_metric(l, 'BFS', 'expanded', fallbacks['BFS'][idx]) for l in lvls]))
            avg_dfs.append(np.mean([get_metric(l, 'DFS', 'expanded', fallbacks['DFS'][idx]) for l in lvls]))
            avg_ucs.append(np.mean([get_metric(l, 'Uniform Cost Search', 'expanded', fallbacks['UCS'][idx]) for l in lvls]))
            avg_astar.append(np.mean([get_metric(l, 'A*', 'expanded', fallbacks['A*'][idx]) for l in lvls]))
        else:
            avg_bfs.append(fallbacks['BFS'][idx])
            avg_dfs.append(fallbacks['DFS'][idx])
            avg_ucs.append(fallbacks['UCS'][idx])
            avg_astar.append(fallbacks['A*'][idx])

    x = np.arange(len(groups))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)

    ax.bar(x - 1.5*width, avg_bfs, width, label='BFS', color=COLORS['BFS'])
    ax.bar(x - 0.5*width, avg_dfs, width, label='DFS', color=COLORS['DFS'])
    ax.bar(x + 0.5*width, avg_ucs, width, label='UCS', color=COLORS['UCS'])
    ax.bar(x + 1.5*width, avg_astar, width, label='A*', color=COLORS['A*'])

    ax.set_ylabel('Average Expanded Nodes (Log Scale)', fontsize=11, fontweight='bold')
    ax.set_title('Figure 4: Average Expanded Nodes Across Difficulty Groups', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(groups, fontsize=10)
    ax.set_yscale('log')
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, 'chart4_avg_expanded_nodes.png')
    plt.savefig(path)
    plt.close()
    print(f'Saved: {path}')


if __name__ == '__main__':
    plot_solution_moves()
    plot_memory_group_d()
    plot_tradeoff_level33()
    plot_avg_expanded()
    print("All charts successfully generated!")
