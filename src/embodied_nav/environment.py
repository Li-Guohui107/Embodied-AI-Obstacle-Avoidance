"""二维栅格环境：地图生成、边界检查、障碍物管理与碰撞检测。"""
from __future__ import annotations

import numpy as np
from typing import Iterable, Tuple

Cell = Tuple[int, int]


class GridWorld:
    """二维栅格世界。坐标使用 (row, col)，即 (行, 列)。"""

    def __init__(self, rows: int = 20, cols: int = 30, seed: int = 7):
        if rows < 3 or cols < 3:
            raise ValueError("地图行数和列数都必须至少为 3。")
        self.rows = rows
        self.cols = cols
        self.rng = np.random.default_rng(seed)
        self.occupancy = np.zeros((rows, cols), dtype=np.uint8)

    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.rows and 0 <= c < self.cols

    def is_free(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and self.occupancy[cell] == 0

    def add_obstacle(self, cell: Cell) -> None:
        if not self.in_bounds(cell):
            raise ValueError(f"障碍物坐标越界：{cell}")
        self.occupancy[cell] = 1

    def add_obstacles(self, cells: Iterable[Cell]) -> None:
        for cell in cells:
            self.add_obstacle(cell)

    def remove_obstacle(self, cell: Cell) -> None:
        if self.in_bounds(cell):
            self.occupancy[cell] = 0

    def random_obstacles(
        self,
        count: int,
        reserved: Iterable[Cell] = (),
    ) -> None:
        """随机放置障碍物；reserved 中的格子不会被占用。"""
        reserved_set = set(reserved)
        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in reserved_set
        ]
        if count > len(candidates):
            raise ValueError("障碍物数量超过可用格子数量。")
        chosen = self.rng.choice(len(candidates), size=count, replace=False)
        for index in chosen:
            self.add_obstacle(candidates[int(index)])

    def neighbors(self, cell: Cell) -> list[Cell]:
        """返回四邻接且可通行的格子。"""
        r, c = cell
        candidates = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        return [p for p in candidates if self.is_free(p)]

    def copy(self) -> "GridWorld":
        other = GridWorld(self.rows, self.cols)
        other.occupancy = self.occupancy.copy()
        return other
