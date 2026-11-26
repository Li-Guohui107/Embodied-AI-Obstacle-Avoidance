"""自定义场景示例：建立地图并调用 A*。"""
from embodied_nav.environment import GridWorld
from embodied_nav.planner import AStarPlanner

world = GridWorld(rows=12, cols=16, seed=3)
world.add_obstacles((r, 7) for r in range(1, 10) if r != 5)

start = (0, 0)
goal = (11, 15)
path = AStarPlanner(world).plan(start, goal)

if path is None:
    print("没有找到可行路径")
else:
    print("规划成功！路径格子数：", len(path))
    print("路径：", path)
