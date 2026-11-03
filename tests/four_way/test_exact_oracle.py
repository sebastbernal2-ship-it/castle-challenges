from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from castle_challenges.games.four_way.rules import payout


@unittest.skipUnless(shutil.which("c++"), "C++ compiler is required for oracle test")
class ExactFullActionOracleTests(unittest.TestCase):
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
