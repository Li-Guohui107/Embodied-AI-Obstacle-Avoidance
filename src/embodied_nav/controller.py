"""简化路径跟踪控制器。"""
from __future__ import annotations

from typing import Sequence
from .environment import Cell, GridWorld


class GridController:
    """每个仿真步向路径上的下一个栅格移动一格。"""

    def __init__(self, world: GridWorld):
        self.world = world

    def next_step(self, current: Cell, path: Sequence[Cell]) -> Cell:
        if not path:
            return current
        try:
            index = path.index(current)
        except ValueError:
            # 当前点不在路径中时，要求上层重新规划。
            raise ValueError("机器人当前位置不在当前路径中，请重新规划。")
        if index >= len(path) - 1:
            return current
        candidate = path[index + 1]
        if not self.world.is_free(candidate):
            raise RuntimeError(f"下一步被障碍物阻挡：{candidate}")
        return candidate
