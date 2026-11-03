import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (Path(__file__).parents[2] / "research" / "four_way"
               / "restricted_support4_search.py")
SPEC = importlib.util.spec_from_file_location("restricted_support4_search", MODULE_PATH)
SEARCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SEARCH)


class SupportFourSearchTests(unittest.TestCase):
    def test_derivative_matches_finite_difference(self):
        actions = [
            (20, 20, 20, 20, 20),
            (100, 0, 0, 0, 0),
            (0, 100, 0, 0, 0),
            (0, 0, 100, 0, 0),
            (0, 0, 0, 100, 0),
            (0, 0, 0, 0, 100),
        ]
        tensor = SEARCH.payoff_tensor(actions)
        support = (0, 1, 3, 5)
        p = (0.15, 0.25, 0.30, 0.30)
        direction = (1.0, 0.0, 0.0, -1.0)
        derivative = SEARCH.derivative(tensor, 2, support, p, direction)
        eps = 1e-6
        plus = (p[0] + eps, p[1], p[2], p[3] - eps)
        minus = (p[0] - eps, p[1], p[2], p[3] + eps)
        finite = (SEARCH.expected_payoff(tensor, 2, support, plus)
                  - SEARCH.expected_payoff(tensor, 2, support, minus)) / (2 * eps)
        self.assertAlmostEqual(derivative, finite, places=6)

    def test_grid_starts_are_interior_simplex_points(self):
        points = list(SEARCH._grid_points(4, 8))
        self.assertTrue(points)
        for point in points:
            p = point + (1 - sum(point),)
            self.assertEqual(len(p), 4)
            self.assertAlmostEqual(sum(p), 1.0)
            self.assertGreater(min(p), 0)


if __name__ == "__main__":
    unittest.main()
