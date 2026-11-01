"""Generate professional academic comparison charts for Bloxorz Solvers benchmark.
Saves high-resolution PNG charts ready to be inserted into the final report.
"""
import os
import matplotlib.pyplot as plt
import numpy as np

# Output directory for charts
CHARTS_DIR = os.path.join(os.path.dirname(__file__), 'charts')
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

# -------------------------------------------------------------
# 1. CHART 1: Solution Length (Moves) Comparison (Selected Levels)
# -------------------------------------------------------------
def plot_solution_moves():
    levels = ['L1\n(Simple)', 'L21\n(Simple)', 'L24\n(Fragile)', 'L22\n(Bridge)', 'L29\n(Split)', 'L30\n(Combined)']
    
    moves_bfs = [4, 7, 28, 17, 24, 57]
    moves_dfs = [4, 43, 36, 120, 1298, 2639]
    moves_ucs = [4, 7, 28, 17, 24, 57]
    moves_astar = [4, 7, 28, 17, 24, 57]

    x = np.arange(len(levels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    
    rects1 = ax.bar(x - 1.5*width, moves_bfs, width, label='BFS', color=COLORS['BFS'])
    rects2 = ax.bar(x - 0.5*width, moves_dfs, width, label='DFS', color=COLORS['DFS'])
    rects3 = ax.bar(x + 0.5*width, moves_ucs, width, label='UCS', color=COLORS['UCS'])
    rects4 = ax.bar(x + 1.5*width, moves_astar, width, label='A*', color=COLORS['A*'])

    ax.set_ylabel('Solution Length (Number of Moves) - Log Scale', fontsize=11, fontweight='bold')
    ax.set_title('Figure 1: Solution Length (Moves) Comparison Across Representative Stages', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(levels, fontsize=10)
    ax.set_yscale('log')
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    # Annotate exact numbers for high DFS bars
    ax.annotate('1,298', xy=(4 - 0.5*width, 1298), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['DFS'])
    ax.annotate('2,639', xy=(5 - 0.5*width, 2639), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['DFS'])
    ax.annotate('24', xy=(4 + 1.5*width, 24), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['A*'])
    ax.annotate('57', xy=(5 + 1.5*width, 57), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=8, fontweight='bold', color=COLORS['A*'])

    plt.tight_layout()
    path = os.path.join(CHARTS_DIR, 'chart1_solution_moves.png')
    plt.savefig(path)
    plt.close()
    print(f'Saved: {path}')


# -------------------------------------------------------------
# 2. CHART 2: Peak Memory Usage (Group D - Complex Combined Stages)
# -------------------------------------------------------------
def plot_memory_group_d():
    levels = ['Level 29', 'Level 30', 'Level 35', 'Level 40', 'Level 51']
    
    mem_bfs = [1315.5, 13791.5, 9936.1, 9435.3, 872.3]
    mem_dfs = [2172.7, 5544.1, 1318.2, 8089.4, 236.7]
    mem_ucs = [1294.3, 13597.6, 9701.5, 9761.2, 850.3]
    mem_astar = [401.9, 3601.9, 3025.2, 3177.9, 277.9]

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
    ax.annotate('A* saves ~10.2 MB RAM!\n(3.6 MB vs 13.8 MB)', 
                xy=(1 + 1.5*width, 3601.9), 
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
    moves = [46, 65, 49, 49]
    costs = [68, 95, 63, 63]

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
        ax.annotate(f'{h}', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')
    for r in rects2:
        h = r.get_height()
        ax.annotate(f'{h}', xy=(r.get_x() + r.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=9, fontweight='bold')

    ax.text(0.5, 0.85, 'BFS minimizes Moves (46 steps)\nUCS & A* minimize Cost (63 cost vs 68)', 
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
    
    avg_bfs = [65.8, 69.3, 249.2, 5953.4]
    avg_dfs = [35.0, 64.7, 224.0, 2674.4]
    avg_ucs = [65.8, 69.7, 249.2, 5865.0]
    avg_astar = [47.6, 68.0, 212.2, 4786.0]

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
