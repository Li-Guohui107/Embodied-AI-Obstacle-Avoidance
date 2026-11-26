"""A* 全局路径规划。"""
from __future__ import annotations

import heapq
from itertools import count
from typing import Optional

from .environment import Cell, GridWorld


def manhattan(a: Cell, b: Cell) -> float:
    """四邻接网格的曼哈顿启发式距离。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class AStarPlanner:
    """在 GridWorld 上执行 A* 搜索。"""

    def __init__(self, world: GridWorld):
        self.world = world
        self.expanded_nodes = 0

    def plan(self, start: Cell, goal: Cell) -> Optional[list[Cell]]:
        if not self.world.is_free(start):
            raise ValueError(f"起点不可通行：{start}")
        if not self.world.is_free(goal):
            raise ValueError(f"目标点不可通行：{goal}")

        frontier = []
        tie_breaker = count()
        heapq.heappush(frontier, (manhattan(start, goal), next(tie_breaker), start))

        came_from: dict[Cell, Optional[Cell]] = {start: None}
        g_cost: dict[Cell, float] = {start: 0.0}
        self.expanded_nodes = 0

        while frontier:
            _, _, current = heapq.heappop(frontier)
            self.expanded_nodes += 1

            if current == goal:
                return self._reconstruct(came_from, goal)

            for neighbor in self.world.neighbors(current):
                tentative_g = g_cost[current] + 1.0
                if tentative_g < g_cost.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_cost[neighbor] = tentative_g
                    f_cost = tentative_g + manhattan(neighbor, goal)
                    heapq.heappush(
                        frontier,
                        (f_cost, next(tie_breaker), neighbor),
                    )
        return None

    @staticmethod
    def _reconstruct(
        came_from: dict[Cell, Optional[Cell]],
        goal: Cell,
    ) -> list[Cell]:
        path = []
        current: Optional[Cell] = goal
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path
