from fractions import Fraction
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[2]
FOUR_WAY = ROOT / "research" / "four_way"
RUNNER_PATH = FOUR_WAY / "run_exact_auxiliary_best_response.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("auxiliary_response_runner", RUNNER_PATH)
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
assert RUNNER_SPEC.loader is not None
RUNNER_SPEC.loader.exec_module(RUNNER)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler is required for oracle test")
class AuxiliaryOracleTests(unittest.TestCase):
    def test_cost_anchor_and_perturbation(self):
        a0 = (20, 20, 20, 20, 20)
        a1 = (19, 20, 20, 20, 21)
        self.assertEqual(RUNNER.action_cost(a0), 0)
        self.assertEqual(RUNNER.action_cost(a1), 1)
        self.assertEqual(RUNNER.action_cost((58, 21, 0, 21, 0)), Fraction(5092, 2500))
        self.assertGreater(RUNNER.action_cost((0, 0, 0, 0, 100)), 2)

    def test_t_one_order_matches_target_game_oracle(self):
        with tempfile.TemporaryDirectory(prefix="four-way-aux-oracle-test-") as temp:
            target = Path(temp) / "target"
            auxiliary = Path(temp) / "auxiliary"
            subprocess.run([
                shutil.which("c++"), "-O2", "-std=c++17", "-pthread",
                str(FOUR_WAY / "exact_full_action_best_response.cpp"),
                "-o", str(target),
            ], check=True, capture_output=True)
            subprocess.run([
                shutil.which("c++"), "-O2", "-std=c++17", "-pthread",
                str(FOUR_WAY / "exact_auxiliary_best_response.cpp"),
                "-o", str(auxiliary),
            ], check=True, capture_output=True)
            mixture = "2\n20 20 20 20 20 500000\n19 20 20 20 21 500000\n"
            target_line = subprocess.run(
                [str(target), "2", "1"], input=mixture, text=True,
                capture_output=True, check=True,
            ).stdout.strip()
            auxiliary_line = subprocess.run(
                [str(auxiliary), "2", "1", "1", "1"], input=mixture, text=True,
                capture_output=True, check=True,
            ).stdout.strip()
            anchor_line = subprocess.run(
                [str(auxiliary), "2", "1", "0", "1"], input=mixture, text=True,
                capture_output=True, check=True,
            ).stdout.strip()
        target_fields = target_line.split("\t")
        auxiliary_fields = auxiliary_line.split("\t")
        self.assertEqual(target_fields[0], auxiliary_fields[0])
        self.assertEqual(
            Fraction(int(target_fields[1]), int(target_fields[2])),
            Fraction(int(auxiliary_fields[1]), int(auxiliary_fields[2])),
        )
        self.assertEqual(anchor_line.split("\t")[0], "20,20,20,20,20")


if __name__ == "__main__":
    unittest.main()
