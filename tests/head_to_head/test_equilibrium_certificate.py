import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[2]
VERIFY_PATH = ROOT / "research" / "head_to_head" / "verify_strategy.py"
VERIFY_SPEC = importlib.util.spec_from_file_location("head_to_head_verify", VERIFY_PATH)
VERIFY = importlib.util.module_from_spec(VERIFY_SPEC)
assert VERIFY_SPEC.loader is not None
VERIFY_SPEC.loader.exec_module(VERIFY)


class ExactEquilibriumCertificateTests(unittest.TestCase):
    def test_saved_strategy_is_legal_and_has_zero_full_action_gap(self):
        path = ROOT / "research" / "head_to_head" / "results" / "exact-equilibrium-flow-lp.json"
        data = json.loads(path.read_text())
        total = data["frequency_total"]
        self.assertEqual(total, 410)
        marginals = [[0] * 101 for _ in range(5)]
        total_weight = 0
        for raw_action, probability in data["strategy"]:
            action = tuple(raw_action)
            weight = round(probability * total)
            self.assertEqual(len(action), 5)
            self.assertEqual(sum(action), 100)
            self.assertGreaterEqual(min(action), 0)
            self.assertGreater(weight, 0)
            total_weight += weight
            for castle, soldiers in enumerate(action):
                marginals[castle][soldiers] += weight
        self.assertEqual(total_weight, total)
        self.assertEqual(marginals, data["marginal_counts"])

        certificate = VERIFY.verify(path)
        self.assertEqual(certificate["exploitability_fraction"][0], 0)
        self.assertEqual(certificate["best_response_score_fraction"], [6150, 820])
        self.assertTrue(certificate["verified_full_action_space"])


if __name__ == "__main__":
    unittest.main()
