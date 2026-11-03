from fractions import Fraction
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from castle_challenges.games.four_way.rules import payout


RUNNER_PATH = (Path(__file__).parents[2] / "research" / "four_way"
               / "run_exact_full_best_response.py")
RUNNER_SPEC = importlib.util.spec_from_file_location("exact_best_response_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler is required for oracle test")
class ExactFullActionOracleTests(unittest.TestCase):
    def test_truncation_has_a_rigorous_total_variation_bound(self):
        actions = [(1, 1, 1, 1, 96), (2, 2, 2, 2, 92), (3, 3, 3, 3, 88)]
        counts = dict(zip(actions, (80, 15, 5)))
        retained, tail = RUNNER._retain_top_support(counts, 1)
        self.assertEqual(retained, {actions[0]: 80})
        self.assertEqual(tail, 20)
        upper = RUNNER._certified_payout_upper_bound(Fraction(8), Fraction(tail, 100))
        self.assertEqual(upper, Fraction(41, 5))
        tv = RUNNER._input_total_variation(actions[:2],
                                           [Fraction(1, 2), Fraction(1, 2)],
                                           retained)
        self.assertEqual(tv, Fraction(1, 2))
        lower, upper = RUNNER._input_exploitability_bounds(Fraction(8), tv)
        self.assertEqual((lower, upper), (Fraction(0), Fraction(21, 4)))
        self.assertEqual(
            RUNNER._input_exploitability_bounds(Fraction(17, 2), Fraction(0)),
            (Fraction(19, 4), Fraction(19, 4)),
        )

    def test_pure_population_matches_profile_rules(self):
        source = (Path(__file__).parents[2] / "research" / "four_way"
                  / "exact_full_action_best_response.cpp")
        with tempfile.TemporaryDirectory(prefix="four-way-exact-oracle-test-") as temp:
            binary = Path(temp) / "oracle"
            subprocess.run([shutil.which("c++"), "-O2", "-std=c++17",
                            str(source), "-o", str(binary)], check=True,
                           stdout=subprocess.DEVNULL)
            result = subprocess.run(
                [str(binary)], input="1\n20 20 20 20 20 1\n", text=True,
                capture_output=True, check=True,
            ).stdout.strip()

        allocation, numerator, denominator, triple_count = result.split("\t")
        response = tuple(map(int, allocation.split(",")))
        opponent = (20, 20, 20, 20, 20)
        self.assertEqual(sum(response), 100)
        self.assertEqual(int(triple_count), 1)
        self.assertEqual((int(numerator), int(denominator)), (36, 4))
        self.assertEqual(payout((response, opponent, opponent, opponent))[0], 9.0)


if __name__ == "__main__":
    unittest.main()
