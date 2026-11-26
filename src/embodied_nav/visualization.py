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
from matplotlib.patches import Rectangle

from .environment import Cell, GridWorld
from .simulation import SimulationResult

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

NEW_OBSTACLE = "#e85d3a"
NEW_OBSTACLE_EDGE = "#9a3412"


def _display_grid(world: GridWorld, hidden: set[Cell] | None) -> object:
    """动画开始前藏起尚未出现的障碍，避免它看起来从第一帧就存在。"""
    if not hidden:
        return world.occupancy
    grid = world.occupancy.copy()
    for cell in hidden:
        if world.in_bounds(cell):
            grid[cell] = 0
    return grid


def _mark_new_obstacles(ax, cells: list[Cell], visible: bool = True) -> list[Rectangle]:
    patches: list[Rectangle] = []
    for row, col in cells:
        patch = Rectangle(
            (col - 0.5, row - 0.5),
            1,
            1,
            facecolor=NEW_OBSTACLE,
            edgecolor=NEW_OBSTACLE_EDGE,
            linewidth=1.6,
            zorder=4,
            visible=visible,
            label="新出现的障碍" if not patches else None,
        )
        ax.add_patch(patch)
        patches.append(patch)
    return patches


def _active_plan(result: SimulationResult, frame: int) -> list[Cell]:
    history = result.path_history
    if not history or not result.planned_paths:
        return []
    current = history[min(frame, len(history) - 1)]
    seen = set(history[: frame + 1])
    chosen: list[Cell] = []
    for path in result.planned_paths:
        if path and path[0] in seen and current in path:
            chosen = path
    return chosen


def _draw_base(
    ax,
    world: GridWorld,
    start: Cell,
    goal: Cell,
    hidden: set[Cell] | None = None,
):
    ax.imshow(
        _display_grid(world, hidden),
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
               linewidths=1.5, label="起点", zorder=5)
    ax.scatter(goal[1], goal[0], s=190, c="#e64b4b", marker="*",
               edgecolors="white", linewidths=1.0, label="目标", zorder=5)
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
    dynamic_cells = [cell for _, cell in result.obstacle_events]
    _mark_new_obstacles(ax, dynamic_cells, visible=True)
    for index, planned in enumerate(result.planned_paths):
        if planned:
            ax.plot(
                [p[1] for p in planned],
                [p[0] for p in planned],
                color="#2878d0",
                linewidth=2.0,
                alpha=0.55,
                label="规划路径" if index == 0 else None,
            )
    if result.path_history:
        ax.plot(
            [p[1] for p in result.path_history],
            [p[0] for p in result.path_history],
            color="#f39c35", linewidth=2.8, label="实际轨迹",
        )
        ax.scatter(result.path_history[-1][1], result.path_history[-1][0],
                   s=100, c="#f39c35", edgecolors="white", zorder=6)
    ax.set_title("自主避障 | 红格是运行途中新出现的障碍", fontsize=15, pad=14)
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
    hidden = {cell for _, cell in result.obstacle_events}
    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    _draw_base(ax, world, start, goal, hidden=hidden)
    new_patches = []
    for step, cell in result.obstacle_events:
        new_patches.append((step, _mark_new_obstacles(ax, [cell], visible=False)[0]))
    plan_line, = ax.plot([], [], color="#2878d0", linewidth=2.3, alpha=0.9, zorder=5, label="规划路径")
    trail, = ax.plot([], [], color="#f39c35", linewidth=2.6, zorder=6, label="实际轨迹")
    robot = ax.scatter([], [], s=150, c="#f39c35", edgecolors="white", zorder=7, label="机器人")
    ax.legend(loc="upper right", frameon=True)
    title = ax.set_title("导航 | 第 0 步")
    # 障碍出现的那一帧多停一会儿，否则一闪而过看不出来。
    frames: list[int] = []
    for index in range(len(history)):
        frames.append(index)
        if any(step == index for step, _ in result.obstacle_events):
            frames.extend([index] * 8)

    def update(frame):
        points = history[: frame + 1]
        trail.set_data([p[1] for p in points], [p[0] for p in points])
        robot.set_offsets([[points[-1][1], points[-1][0]]])
        plan = _active_plan(result, frame)
        if len(plan) >= 2:
            plan_line.set_data([p[1] for p in plan], [p[0] for p in plan])
        else:
            plan_line.set_data([], [])
        appeared = False
        for step, patch in new_patches:
            show = frame >= step
            patch.set_visible(show)
            appeared = appeared or show
        if frame == len(history) - 1 and result.reached_goal:
            note = "已到达目标"
        elif any(frame == step for step, _ in result.obstacle_events):
            note = "新障碍挡住路口，重新规划"
        elif appeared:
            note = "沿新路径绕行"
        else:
            note = "沿规划路径前进"
        title.set_text(f"导航 | 第 {frame}/{len(history) - 1} 步 | {note}")
        return trail, plan_line, robot, title

    animation = FuncAnimation(
        fig, update, frames=frames, interval=interval, blit=False,
        repeat=False,
    )
    animation.save(output_path, writer=PillowWriter(fps=6))
    plt.close(fig)
