"""命令行入口：python -m embodied_nav.main"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .environment import GridWorld
from .simulation import NavigationSimulation


def build_demo_world(seed: int = 7):
    rows, cols = 20, 30
    start = (1, 1)
    goal = (18, 28)
    world = GridWorld(rows, cols, seed=seed)

    # 形成几段墙体，并保留通道，确保初始地图存在路径。
    walls = []
    for r in range(2, 17):
        if r not in (6, 7):
            walls.append((r, 8))
    for r in range(3, 19):
        if r not in (12, 13):
            walls.append((r, 17))
    for c in range(10, 26):
        if c not in (19, 20):
            walls.append((10, c))
    world.add_obstacles(walls)

    # 随机散布少量障碍物，避免起点、目标和主要通道。
    reserved = set(walls) | {start, goal}
    world.random_obstacles(35, reserved=reserved)
    return world, start, goal


def main():
    parser = argparse.ArgumentParser(description="机器人自主避障教学演示")
    parser.add_argument("--seed", type=int, default=7, help="随机种子")
    parser.add_argument("--no-animation", action="store_true", help="不生成 GIF")
    parser.add_argument("--output", type=str, default="outputs", help="输出目录")
    parser.add_argument(
        "--view",
        choices=("2d", "3d", "both"),
        default="2d",
        help="可视化：2d 俯视图、3d 立体场景，或 both",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="额外打开可拖拽旋转的 3D 窗口",
    )
    args = parser.parse_args()

    if args.interactive:
        os.environ["EMBODIED_NAV_INTERACTIVE"] = "1"
        import matplotlib
        matplotlib.use("TkAgg")

    from .visualization import save_animation, save_static_plot
    from .visualization_3d import (
        save_animation_3d,
        save_static_plot_3d,
        show_interactive_3d,
    )

    world, start, goal = build_demo_world(args.seed)

    # 第 12 个执行步时，在路径附近放置动态障碍物，演示重规划。
    dynamic_obstacle = (12, (7, 8))
    simulation = NavigationSimulation(
        world, start, goal, dynamic_obstacle=dynamic_obstacle
    )
    result = simulation.run()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    want_2d = args.view in ("2d", "both")
    want_3d = args.view in ("3d", "both") or args.interactive
    if want_2d:
        save_static_plot(world, start, goal, result, output_dir / "navigation_demo.png")
        if not args.no_animation:
            save_animation(
                world, start, goal, result, output_dir / "navigation_demo.gif"
            )
    if want_3d:
        save_static_plot_3d(
            world, start, goal, result, output_dir / "navigation_demo_3d.png"
        )
        if not args.no_animation:
            save_animation_3d(
                world, start, goal, result, output_dir / "navigation_demo_3d.gif"
            )
    executed_steps = max(0, len(result.path_history) - 1)
    path_length = sum(
        abs(a[0] - b[0]) + abs(a[1] - b[1])
        for a, b in zip(result.path_history, result.path_history[1:])
    )
    print("\n========== 仿真实验结果 ==========")
    print(f"任务状态：{'成功' if result.reached_goal else '未完成'}")
    print(f"说明：{result.message}")
    print(f"执行步数：{executed_steps}")
    print(f"实际路径长度：{path_length}")
    print(f"搜索扩展节点总数：{result.expanded_nodes_total}")
    print(f"重新规划次数：{result.replans}")
    print(f"输出目录：{output_dir.resolve()}")
    print("==================================\n")
    if args.interactive:
        show_interactive_3d(world, start, goal, result)


if __name__ == "__main__":
    main()
