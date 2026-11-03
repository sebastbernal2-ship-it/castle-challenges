import unittest

from castle_challenges.game import allocations, castle_points, four_way_payout, head_to_head
from castle_challenges.simulation import evaluate_head_to_head


class GameTests(unittest.TestCase):
    def test_allocation_count_and_sum(self):
        self.assertEqual(sum(1 for _ in allocations(4)), 70)
        self.assertTrue(all(sum(a) == 4 for a in allocations(4)))

    def test_head_to_head(self):
        a = (20, 20, 20, 20, 20)
        self.assertEqual(head_to_head(a, a), 7.5)
        self.assertEqual(head_to_head((100, 0, 0, 0, 0), (0, 0, 0, 0, 100)), 5.5)
        self.assertAlmostEqual(head_to_head(a, (0, 0, 0, 0, 100)) +
                               head_to_head((0, 0, 0, 0, 100), a), 15.0)

    def test_castle_ties_and_rank_payout_ties(self):
        p = (50, 50, 0, 0, 0)
        self.assertEqual(castle_points((p, p, p, p)), (3.75,) * 4)
        self.assertEqual(four_way_payout((p, p, p, p)), (3.75,) * 4)

    def test_rank_tie_splits_positions(self):
        # Winners tie on all castle points; lower-ranked players likewise tie.
        a = (100, 0, 0, 0, 0)
        b = (0, 100, 0, 0, 0)
        payouts = four_way_payout((a, b, (0, 0, 100, 0, 0), (0, 0, 0, 100, 0)))
        self.assertAlmostEqual(sum(payouts), 15)

    def test_simulation_seed_reproducible(self):
        a = (20, 20, 20, 20, 20)
        self.assertEqual(evaluate_head_to_head(a, [a], 50, 3),
                         evaluate_head_to_head(a, [a], 50, 3))


if __name__ == "__main__":
    unittest.main()
