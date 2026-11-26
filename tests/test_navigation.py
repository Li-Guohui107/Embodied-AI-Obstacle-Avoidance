import unittest

from embodied_nav.environment import GridWorld
from embodied_nav.planner import AStarPlanner
from embodied_nav.simulation import NavigationSimulation


class TestAStar(unittest.TestCase):
    def test_shortest_path_without_obstacles(self):
        world = GridWorld(5, 6)
        path = AStarPlanner(world).plan((0, 0), (4, 5))
        self.assertIsNotNone(path)
        self.assertEqual(len(path) - 1, 9)

    def test_obstacle_is_avoided(self):
        world = GridWorld(5, 5)
        world.add_obstacle((2, 2))
        path = AStarPlanner(world).plan((2, 0), (2, 4))
        self.assertIsNotNone(path)
        self.assertNotIn((2, 2), path)

    def test_unreachable_goal(self):
        world = GridWorld(3, 3)
        world.add_obstacles([(0, 1), (1, 0), (1, 2), (2, 1)])
        path = AStarPlanner(world).plan((0, 0), (2, 2))
        self.assertIsNone(path)

    def test_simulation_reaches_goal(self):
        world = GridWorld(8, 10)
        world.add_obstacles((r, 4) for r in range(1, 7) if r != 3)
        sim = NavigationSimulation(world, (0, 0), (7, 9))
        result = sim.run()
        self.assertTrue(result.reached_goal)


if __name__ == "__main__":
    unittest.main()
