"""把同一套栅格导航结果画成三维场景：地面、墙体、路径和机器人。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib

if os.environ.get("EMBODIED_NAV_INTERACTIVE") != "1" and "matplotlib.pyplot" not in sys.modules:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .environment import Cell, GridWorld
from .simulation import SimulationResult

# 与二维图同一套颜色，墙体抬高后仍能对照阅读。
FLOOR = "#e4edf6"
FLOOR_EDGE = "#b7c4d4"
WALL = "#2b3a4f"
WALL_EDGE = "#1b2636"
DYNAMIC = "#e85d3a"
DYNAMIC_EDGE = "#9a3412"
PATH = "#2878d0"
TRAIL = "#f39c35"
ROBOT = "#f39c35"
START = "#16a36a"
GOAL = "#e64b4b"
BACKGROUND = "#f4f7fb"

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _occupied_cells(world: GridWorld, hidden: set[Cell]) -> list[Cell]:
    cells: list[Cell] = []
    for row in range(world.rows):
        for col in range(world.cols):
            cell = (row, col)
            if world.occupancy[cell] and cell not in hidden:
                cells.append(cell)
    return cells


def _draw_boxes(
    ax,
    cells: list[Cell],
    height: float,
    color: str,
    edgecolor: str,
    z0: float = 0.0,
    size: float = 0.9,
) -> Poly3DCollection | None:
    if not cells:
        return None
    inset = (1.0 - size) / 2.0
    xs = np.array([col - 0.5 + inset for _, col in cells], dtype=float)
    ys = np.array([row - 0.5 + inset for row, _ in cells], dtype=float)
    zs = np.full(len(cells), z0, dtype=float)
    artist = ax.bar3d(
        xs,
        ys,
        zs,
        size,
        size,
        height,
        color=color,
        shade=True,
        edgecolor=edgecolor,
        linewidth=0.3,
        zorder=3,
    )
    return artist


def _setup_ax(ax, world: GridWorld) -> None:
    rows, cols = world.rows, world.cols
    ax.set_xlim(-0.5, cols - 0.5)
    ax.set_ylim(-0.5, rows - 0.5)
    ax.set_zlim(0, 2.2)
    # x、y 按格子等比。z 只留出墙高，避免场景被拉成一根柱子。
    ax.set_box_aspect((cols, rows, 8))
    ax.view_init(elev=34, azim=-56)
    ax.set_proj_type("persp")
    # 关闭按相机深度整层排序，否则整块地面会盖住贴地的路径。
    ax.computed_zorder = False
    ax.set_axis_off()
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((1, 1, 1, 0))
        axis.line.set_color((1, 1, 1, 0))


def _draw_floor(ax, world: GridWorld) -> None:
    rows, cols = world.rows, world.cols
    xx, yy = np.meshgrid(
        np.array([-0.55, cols - 0.45]),
        np.array([-0.55, rows - 0.45]),
    )
    ax.plot_surface(
        xx, yy, np.zeros_like(xx), color=FLOOR, shade=False, zorder=0,
    )
    grid_z = 0.03
    for col in range(cols + 1):
        ax.plot(
            [col - 0.5, col - 0.5], [-0.5, rows - 0.5], [grid_z, grid_z],
            color="#d3ddea", linewidth=0.45, zorder=1,
        )
    for row in range(rows + 1):
        ax.plot(
            [-0.5, cols - 0.5], [row - 0.5, row - 0.5], [grid_z, grid_z],
            color="#d3ddea", linewidth=0.45, zorder=1,
        )
    border_x = [-0.5, cols - 0.5, cols - 0.5, -0.5, -0.5]
    border_y = [-0.5, -0.5, rows - 0.5, rows - 0.5, -0.5]
    ax.plot(border_x, border_y, [0.04] * 5, color=FLOOR_EDGE, linewidth=1.15, zorder=2)


def _draw_markers(ax, start: Cell, goal: Cell) -> None:
    ax.bar3d(
        [start[1] - 0.22], [start[0] - 0.22], [0.0],
        0.44, 0.44, 0.16,
        color=START, shade=True, edgecolor="white", linewidth=0.3, zorder=4,
    )
    ax.bar3d(
        [goal[1] - 0.045], [goal[0] - 0.045], [0.0],
        0.09, 0.09, 1.25,
        color=GOAL, shade=True, edgecolor="#ffffff", linewidth=0.2, zorder=4,
    )
    ax.scatter(
        [goal[1]], [goal[0]], [1.4],
        s=160, c=GOAL, marker="*", depthshade=False, zorder=9,
    )


def _legend(ax, has_dynamic: bool) -> None:
    handles = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=WALL,
               markeredgecolor=WALL_EDGE, markersize=8, label="障碍物"),
        Line2D([0], [0], color=PATH, linewidth=2.2, label="规划路径"),
        Line2D([0], [0], color=TRAIL, linewidth=2.2, label="实际轨迹"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=START,
               markersize=8, label="起点"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=GOAL,
               markersize=12, label="目标"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=ROBOT,
               markeredgecolor="white", markersize=8, label="机器人"),
    ]
    if has_dynamic:
        handles.insert(
            1,
            Line2D([0], [0], marker="s", color="none", markerfacecolor=DYNAMIC,
                   markeredgecolor=DYNAMIC_EDGE, markersize=8, label="新出现的障碍"),
        )
    ax.legend(
        handles=handles,
        loc="upper left",
        frameon=True,
        fontsize=8,
        framealpha=0.92,
    )


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


def _dynamic_cells_at(result: SimulationResult, frame: int | None) -> list[Cell]:
    """frame 为 None 时返回最终出现过的全部动态障碍。"""
    cells: list[Cell] = []
    for step, cell in result.obstacle_events:
        if frame is None or frame >= step:
            cells.append(cell)
    return cells


def _new_figure(world: GridWorld):
    fig = plt.figure(figsize=(13.2, 6.4), facecolor=BACKGROUND)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(BACKGROUND)
    _setup_ax(ax, world)
    _draw_floor(ax, world)
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=0.90)
    return fig, ax


def _line3d(ax, cells: list[Cell], color: str, linewidth: float, alpha: float, z: float):
    if len(cells) < 2:
        return None
    return ax.plot(
        [cell[1] for cell in cells],
        [cell[0] for cell in cells],
        [z] * len(cells),
        color=color,
        linewidth=linewidth,
        alpha=alpha,
        zorder=6,
        solid_capstyle="round",
    )


def save_static_plot_3d(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    result: SimulationResult,
    output_path: str | Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dynamic_cells = _dynamic_cells_at(result, None)
    fig, ax = _new_figure(world)
    _draw_boxes(ax, _occupied_cells(world, set(dynamic_cells)), 0.62, WALL, WALL_EDGE)
    _draw_boxes(ax, dynamic_cells, 0.95, DYNAMIC, DYNAMIC_EDGE)
    _draw_markers(ax, start, goal)
    for planned in result.planned_paths:
        _line3d(ax, planned, PATH, 2.4, 0.55, 0.2)
    _line3d(ax, result.path_history, TRAIL, 3.2, 1.0, 0.28)
    if result.path_history:
        last = result.path_history[-1]
        ax.scatter(
            [last[1]], [last[0]], [0.48],
            s=160, c=ROBOT, edgecolors="white", linewidths=0.8,
            depthshade=False, zorder=8,
        )
    status = "已到达目标" if result.reached_goal else "未到达目标"
    ax.set_title(
        f"三维栅格导航  |  {status}  |  重规划 {result.replans} 次",
        fontsize=14, color="#1d2733", pad=8,
    )
    _legend(ax, bool(dynamic_cells))
    fig.savefig(
        output_path, dpi=160, facecolor=fig.get_facecolor(),
        bbox_inches="tight", pad_inches=0.18,
    )
    plt.close(fig)


def _make_animation(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    result: SimulationResult,
    interval: int,
    orbit: bool,
    repeat: bool,
) -> tuple[plt.Figure, FuncAnimation]:
    history = result.path_history or [start]
    dynamic_all = [cell for _, cell in result.obstacle_events]
    hidden = set(dynamic_all)
    fig, ax = _new_figure(world)
    _draw_boxes(ax, _occupied_cells(world, hidden), 0.62, WALL, WALL_EDGE)
    dynamic_artist = _draw_boxes(ax, dynamic_all, 0.95, DYNAMIC, DYNAMIC_EDGE)
    if dynamic_artist is not None:
        dynamic_artist.set_visible(False)
    _draw_markers(ax, start, goal)
    _legend(ax, bool(dynamic_all))

    plan_line, = ax.plot([], [], [], color=PATH, linewidth=2.6, alpha=0.9, zorder=5)
    trail_line, = ax.plot([], [], [], color=TRAIL, linewidth=3.2, alpha=1.0, zorder=6)
    robot = ax.scatter(
        [history[0][1]], [history[0][0]], [0.48],
        s=180, c=ROBOT, edgecolors="white", linewidths=0.8,
        depthshade=False, zorder=8,
    )
    title = ax.set_title("三维栅格导航", fontsize=14, color="#1d2733", pad=8)
    base_azim = -64.0

    def update(frame: int):
        points = history[: frame + 1]
        trail_line.set_data([p[1] for p in points], [p[0] for p in points])
        trail_line.set_3d_properties([0.28] * len(points))

        plan = _active_plan(result, frame)
        if len(plan) >= 2:
            plan_line.set_data([p[1] for p in plan], [p[0] for p in plan])
            plan_line.set_3d_properties([0.2] * len(plan))
        else:
            plan_line.set_data([], [])
            plan_line.set_3d_properties([])

        current = points[-1]
        robot._offsets3d = ([current[1]], [current[0]], [0.48])

        if dynamic_artist is not None:
            visible = any(frame >= step for step, _ in result.obstacle_events)
            dynamic_artist.set_visible(visible)

        just_blocked = any(frame == step for step, _ in result.obstacle_events)
        on_new_plan = bool(plan and result.planned_paths and plan != result.planned_paths[0])
        if frame == len(history) - 1 and result.reached_goal:
            note = "已到达目标"
        elif just_blocked:
            note = "出现障碍，重新规划"
        elif on_new_plan:
            note = "跟踪新路径"
        else:
            note = "跟踪路径"
        title.set_text(
            f"三维栅格导航  |  步 {frame}/{len(history) - 1}  |  {note}"
        )
        if orbit and len(history) > 1:
            ax.view_init(elev=34, azim=base_azim + 26.0 * frame / (len(history) - 1))
        return trail_line, plan_line, robot, title

    animation = FuncAnimation(
        fig, update, frames=len(history), interval=interval, blit=False, repeat=repeat,
    )
    return fig, animation


def save_animation_3d(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    result: SimulationResult,
    output_path: str | Path,
    interval: int = 180,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, animation = _make_animation(
        world, start, goal, result, interval, orbit=True, repeat=False,
    )
    animation.save(output_path, writer=PillowWriter(fps=6), dpi=110)
    plt.close(fig)


def show_interactive_3d(
    world: GridWorld,
    start: Cell,
    goal: Cell,
    result: SimulationResult,
    interval: int = 180,
) -> None:
    """打开可拖拽旋转的窗口。相机不自动转动，方便自己转着看。"""
    fig, animation = _make_animation(
        world, start, goal, result, interval, orbit=False, repeat=True,
    )
    # 动画对象必须留在函数作用域之外，否则窗口还没画就被回收。
    fig._embodied_nav_animation = animation
    plt.show()
