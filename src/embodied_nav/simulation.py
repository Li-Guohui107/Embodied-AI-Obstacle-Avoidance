"""导航闭环仿真：规划、执行、检测路径变化与重新规划。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .environment import Cell, GridWorld
from .planner import AStarPlanner
from .controller import GridController


@dataclass
class SimulationResult:
    path_history: list[Cell] = field(default_factory=list)
    planned_paths: list[list[Cell]] = field(default_factory=list)
    # (执行步, 格子)。步号与 path_history 的帧号对齐：该帧起障碍物已经出现。
    obstacle_events: list[tuple[int, Cell]] = field(default_factory=list)
    expanded_nodes_total: int = 0
    replans: int = 0
    reached_goal: bool = False
    message: str = ""


class NavigationSimulation:
    def __init__(
        self,
        world: GridWorld,
        start: Cell,
        goal: Cell,
        dynamic_obstacle: Optional[tuple[int, Cell]] = None,
        max_steps: int = 2000,
    ):
        self.world = world
        self.start = start
        self.goal = goal
        self.dynamic_obstacle = dynamic_obstacle
        self.max_steps = max_steps
        self.planner = AStarPlanner(world)
        self.controller = GridController(world)

    def run(self) -> SimulationResult:
        result = SimulationResult(path_history=[self.start])
        current = self.start
        path = self.planner.plan(current, self.goal)
        if path is None:
            result.message = "初始地图中不存在可行路径。"
            return result

        result.planned_paths.append(path.copy())
        result.expanded_nodes_total += self.planner.expanded_nodes

        obstacle_added = False
        for step in range(self.max_steps):
            if (
                self.dynamic_obstacle is not None
                and not obstacle_added
                and step == self.dynamic_obstacle[0]
            ):
                obstacle_cell = self.dynamic_obstacle[1]
                # 避免把障碍物直接放到机器人或目标点上。
                if obstacle_cell not in (current, self.goal) and self.world.is_free(obstacle_cell):
                    self.world.add_obstacle(obstacle_cell)
                    result.obstacle_events.append((step, obstacle_cell))
                obstacle_added = True

            if current == self.goal:
                result.reached_goal = True
                result.message = "机器人成功到达目标点。"
                break

            # 检查剩余路径是否仍安全；若动态障碍切断路径，则重新规划。
            try:
                current_index = path.index(current)
                remaining = path[current_index:]
            except ValueError:
                remaining = []

            blocked = any(not self.world.is_free(cell) for cell in remaining[1:])
            if blocked or not remaining:
                new_path = self.planner.plan(current, self.goal)
                result.expanded_nodes_total += self.planner.expanded_nodes
                result.replans += 1
                if new_path is None:
                    result.message = "路径被阻断，且当前地图中不存在新路径。"
                    break
                path = new_path
                result.planned_paths.append(path.copy())

            try:
                current = self.controller.next_step(current, path)
            except (ValueError, RuntimeError):
                new_path = self.planner.plan(current, self.goal)
                result.expanded_nodes_total += self.planner.expanded_nodes
                result.replans += 1
                if new_path is None:
                    result.message = "控制执行失败，且重新规划未找到路径。"
                    break
                path = new_path
                result.planned_paths.append(path.copy())
                current = self.controller.next_step(current, path)

            result.path_history.append(current)

        if not result.message:
            result.reached_goal = current == self.goal
            result.message = (
                "机器人成功到达目标点。"
                if result.reached_goal
                else "达到最大仿真步数，任务未完成。"
            )
        return result
