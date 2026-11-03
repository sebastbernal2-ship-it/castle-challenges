import importlib.util
from pathlib import Path
import shutil
import unittest


MODULE_PATH = (Path(__file__).parents[2] / "research" / "four_way"
               / "restricted_support3_search.py")
SPEC = importlib.util.spec_from_file_location("restricted_support3_search", MODULE_PATH)
SEARCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SEARCH)


class SupportThreeSearchTests(unittest.TestCase):
    def test_payoff_derivative_matches_finite_difference(self):
        actions = [
            (20, 20, 20, 20, 20),
            (100, 0, 0, 0, 0),
            (0, 100, 0, 0, 0),
            (0, 0, 0, 100, 0),
            (0, 0, 0, 0, 100),
        ]
        tensor = SEARCH.payoff_tensor(actions)
        support = (0, 3, 4)
        p = (0.23, 0.31, 0.46)
        direction = (1.0, 0.0, -1.0)
        derivative = SEARCH.payoff_derivative(tensor, 1, support, p, direction)
        epsilon = 1e-6
        plus = (p[0] + epsilon, p[1], p[2] - epsilon)
        minus = (p[0] - epsilon, p[1], p[2] + epsilon)
        finite = (SEARCH.payoff(tensor, 1, support, plus)
                  - SEARCH.payoff(tensor, 1, support, minus)) / (2 * epsilon)
        self.assertAlmostEqual(derivative, finite, places=6)

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler is required for exact oracle")
    def test_restricted_support3_is_globally_exploitable(self):
        pool = Path(__file__).parents[2] / "research" / "four_way" / "baseline_population.json"
        result = SEARCH.search(pool, max_actions=6, grid_denominator=8)
        self.assertGreaterEqual(result["restricted_equilibria_found"], 1)
        self.assertEqual(result["best_candidate"]["exploitability_fraction"], [21, 4])


if __name__ == "__main__":
    unittest.main()
