import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from castle_challenges.games.four_way.rules import payout


class RestrictedPayoffTensorTests(unittest.TestCase):
    def test_native_kernel_matches_rules_for_every_opponent_triple(self):
        compiler = shutil.which("c++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        source = (Path(__file__).parents[2] / "research/four_way/restricted_payoff_tensor.cpp")
        with tempfile.TemporaryDirectory() as directory:
            library_path = Path(directory) / "payoff.so"
            subprocess.run(
                [compiler, "-O3", "-std=c++17", "-shared", "-fPIC",
                 str(source), "-o", str(library_path)],
                check=True, capture_output=True, text=True,
            )
            library = ctypes.CDLL(str(library_path))
            kernel = library.four_way_payoff_tensor
            kernel.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                               ctypes.POINTER(ctypes.c_uint8)]
            kernel.restype = None
            actions = [
                (20, 20, 20, 20, 20),
                (100, 0, 0, 0, 0),
                (0, 100, 0, 0, 0),
                (0, 0, 100, 0, 0),
                (0, 0, 0, 100, 0),
                (0, 0, 0, 0, 100),
            ]
            n = len(actions)
            triple_count = n * (n + 1) * (n + 2) // 6
            flat = (ctypes.c_int * (5 * n))(*(x for action in actions for x in action))
            output = (ctypes.c_uint8 * (n * triple_count))()
            kernel(flat, n, output)

            triple = 0
            for j in range(n):
                for k in range(j, n):
                    for ell in range(k, n):
                        for i, action in enumerate(actions):
                            expected = round(4 * payout((action, actions[j], actions[k], actions[ell]))[0])
                            self.assertEqual(output[i * triple_count + triple], expected)
                        triple += 1


if __name__ == "__main__":
    unittest.main()
