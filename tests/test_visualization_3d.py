import tempfile
import unittest
from pathlib import Path

from embodied_nav.environment import GridWorld
from embodied_nav.simulation import NavigationSimulation
from embodied_nav.visualization_3d import save_static_plot_3d


class TestVisualization3D(unittest.TestCase):
    def test_static_scene_is_written(self):
        world = GridWorld(6, 8, seed=1)
        world.add_obstacles((row, 3) for row in range(2, 5))
        start, goal = (1, 1), (4, 6)
        result = NavigationSimulation(
            world, start, goal, dynamic_obstacle=(2, (2, 4))
        ).run()

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nav3d.png"
            save_static_plot_3d(world, start, goal, result, output)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
