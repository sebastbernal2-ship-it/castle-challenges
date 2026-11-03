import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (Path(__file__).parents[2] / "research" / "four_way"
               / "restricted_two_support_search.py")
SPEC = importlib.util.spec_from_file_location("restricted_two_support_search", MODULE_PATH)
SEARCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SEARCH)


class TwoSupportSearchTests(unittest.TestCase):
    def test_isolates_all_cubic_roots_on_unit_interval(self):
        roots = SEARCH._roots_unit_interval((-8, 66, -150, 100))
        self.assertEqual(len(roots), 3)
        for actual, expected in zip(roots, (0.2, 0.5, 0.8)):
            self.assertAlmostEqual(actual, expected, places=10)

    def test_indifference_polynomial_matches_mixture_evaluation(self):
        a = (100, 0, 0, 0, 0)
        b = (20, 20, 20, 20, 20)
        coeff = SEARCH._indifference_polynomial(a, b)
        x = 0.37
        expected = 0.0
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    opponents = (a if i == 0 else b,
                                 a if j == 0 else b,
                                 a if k == 0 else b)
                    probability = (x if i == 0 else 1 - x)
                    probability *= x if j == 0 else 1 - x
                    probability *= x if k == 0 else 1 - x
                    expected += probability * 4 * (
                        SEARCH.payout((a, *opponents))[0]
                        - SEARCH.payout((b, *opponents))[0]
                    )
        self.assertAlmostEqual(SEARCH._poly_value(coeff, x), expected, places=10)


if __name__ == "__main__":
    unittest.main()
