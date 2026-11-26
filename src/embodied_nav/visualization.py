"""静态结果图与 GIF 动画生成。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib

# 无界面环境也能保存图片。交互模式由入口先选定图形后端。
if os.environ.get("EMBODIED_NAV_INTERACTIVE") != "1" and "matplotlib.pyplot" not in sys.modules:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

from .environment import Cell, GridWorld
from .simulation import SimulationResult


def _draw_base(ax, world: GridWorld, start: Cell, goal: Cell):
    ax.imshow(
        world.occupancy,
        cmap=ListedColormap(["#f4f7fb", "#263449"]),
        vmin=0,
        vmax=1,
        interpolation="none",
    )
    ax.set_xticks(range(world.cols))
    ax.set_yticks(range(world.rows))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_xticks([x - 0.5 for x in range(1, world.cols)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, world.rows)], minor=True)
    ax.grid(which="minor", color="#d8e0ea", linewidth=0.5)
    ax.scatter(start[1], start[0], s=150, c="#16a36a", edgecolors="white",
               linewidths=1.5, label="Start", zorder=5)
    ax.scatter(goal[1], goal[0], s=190, c="#e64b4b", marker="*",
               edgecolors="white", linewidths=1.0, label="Goal", zorder=5)
    ax.set_xlim(-0.5, world.cols - 0.5)
    ax.set_ylim(world.rows - 0.5, -0.5)
    ax.set_aspect("equal")


def save_static_plot(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    result: SimulationResult,
    output_path: str | Path,
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)
    _draw_base(ax, world, start, goal)
    for planned in result.planned_paths:
        if planned:
            ax.plot([p[1] for p in planned], [p[0] for p in planned],
                    color="#2878d0", linewidth=2.0, alpha=0.55)
    if result.path_history:
        ax.plot(
            [p[1] for p in result.path_history],
            [p[0] for p in result.path_history],
            color="#f39c35", linewidth=2.8, label="Executed trajectory",
        )
        ax.scatter(result.path_history[-1][1], result.path_history[-1][0],
                   s=100, c="#f39c35", edgecolors="white", zorder=6)
    ax.set_title("Embodied AI | Autonomous Obstacle Avoidance", fontsize=15, pad=14)
    ax.set_xlabel("Column")
    ax.set_ylabel("Row")
    ax.legend(loc="upper right", frameon=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_animation(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    result: SimulationResult,
    output_path: str | Path,
    interval: int = 180,
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    history = result.path_history or [start]
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    _draw_base(ax, world, start, goal)
    trail, = ax.plot([], [], color="#2878d0", linewidth=2.4, alpha=0.8)
    robot = ax.scatter([], [], s=150, c="#f39c35", edgecolors="white", zorder=7)
    title = ax.set_title("Robot navigation | step 0")

    def update(frame):
        points = history[: frame + 1]
        trail.set_data([p[1] for p in points], [p[0] for p in points])
        robot.set_offsets([[points[-1][1], points[-1][0]]])
        title.set_text(f"Robot navigation | step {frame}/{len(history)-1}")
        return trail, robot, title

    animation = FuncAnimation(
        fig, update, frames=len(history), interval=interval, blit=False,
        repeat=False,
    )
    animation.save(output_path, writer=PillowWriter(fps=6))
    plt.close(fig)
