import importlib.util
import unittest

if importlib.util.find_spec("numpy") and importlib.util.find_spec("scipy"):
    from research.four_way.symmetric_minimax_expansion import (
        payoff_and_jacobian,
        payoff_tensor,
        prune_pool_support,
    )
    import numpy as np
else:
    payoff_and_jacobian = payoff_tensor = prune_pool_support = np = None


@unittest.skipIf(np is None, "install the optional research dependencies")
class SymmetricMinimaxTests(unittest.TestCase):
    def test_support_pruning_keeps_and_renormalizes_active_mass(self):
        actions = [(1,), (2,), (3,)]
        kept, probabilities = prune_pool_support(actions, [0.25, 1e-10, 0.75], 1e-8)
        self.assertEqual(kept, [actions[0], actions[2]])
        np.testing.assert_allclose(probabilities, [0.25, 0.75])

    def test_payoff_jacobian_and_constant_sum_identity(self):
        actions = [
            (20, 20, 20, 20, 20),
            (100, 0, 0, 0, 0),
            (0, 100, 0, 0, 0),
            (0, 0, 100, 0, 0),
            (0, 0, 0, 100, 0),
            (0, 0, 0, 0, 100),
        ]
        triples, multiplicities, tensor = payoff_tensor(actions)
        self.assertEqual(tensor.dtype, np.uint8)
        p = np.array([0.16, 0.12, 0.20, 0.17, 0.21, 0.14])
        utilities, jacobian = payoff_and_jacobian(p, triples, multiplicities, tensor)
        self.assertAlmostEqual(float(p @ utilities), 3.75, places=12)

        epsilon = 1e-6
        for coordinate in range(len(p) - 1):
            direction = np.zeros(len(p))
            direction[coordinate] = 1.0
            direction[-1] = -1.0
            plus = payoff_and_jacobian(
                p + epsilon * direction, triples, multiplicities, tensor
            )[0]
            minus = payoff_and_jacobian(
                p - epsilon * direction, triples, multiplicities, tensor
            )[0]
            finite_difference = (plus - minus) / (2 * epsilon)
            analytic = jacobian[:, coordinate] - jacobian[:, -1]
            np.testing.assert_allclose(finite_difference, analytic, atol=2e-8, rtol=2e-8)


if __name__ == "__main__":
    unittest.main()
