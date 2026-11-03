import importlib.util
from pathlib import Path
import shutil
import unittest


MODULE_PATH = (Path(__file__).parents[2] / "research" / "head_to_head"
               / "run_mirror_prox_flow.py")
SPEC = importlib.util.spec_from_file_location("run_mirror_prox_flow", MODULE_PATH)
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUNNER)


@unittest.skipUnless(shutil.which("c++"), "C++ compiler is required for flow-kernel test")
class MirrorProxFlowTests(unittest.TestCase):
    def test_short_run_decomposes_to_legal_quantized_allocations(self):
        result = RUNNER.run(iterations=20, eta=0.03, frequency_total=1000)
        self.assertEqual(result["iterations"], 20)
        self.assertGreater(result["flow_decomposition_support"], 0)
        self.assertGreater(result["quantized_support"], 0)
        probabilities = result["strategy"]
        counts = [round(probability * 1000) for _, probability in probabilities]
        self.assertEqual(sum(counts), 1000)
        for action, _ in probabilities:
            self.assertEqual(sum(action), 100)
            self.assertEqual(len(action), 5)


if __name__ == "__main__":
    unittest.main()
