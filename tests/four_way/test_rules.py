import unittest

from castle_challenges.games.four_way.best_response import expected_payout
from castle_challenges.games.four_way.rules import castle_points, payout


class FourWayTests(unittest.TestCase):
    def test_all_players_tied(self):
        strategy = (50, 50, 0, 0, 0)
        players = (strategy,) * 4
        self.assertEqual(castle_points(players), (3.75,) * 4)
        self.assertEqual(payout(players), (3.75,) * 4)

    def test_rejects_non_100_soldier_profiles(self):
        with self.assertRaises(ValueError):
            castle_points(((0, 0, 0, 0, 0),) * 4)

    def test_payouts_sum_to_pool(self):
        players = ((100, 0, 0, 0, 0), (0, 100, 0, 0, 0),
                   (0, 0, 100, 0, 0), (0, 0, 0, 100, 0))
        self.assertAlmostEqual(sum(payout(players)), 15.0)

    def test_exact_mixture_evaluation(self):
        strategy = (20, 20, 20, 20, 20)
        population = {strategy: 0.5, (100, 0, 0, 0, 0): 0.5}
        expected = sum(prob * payout((strategy, *opponents))[0]
                       for opponents, prob in [
                           ((strategy, strategy, strategy), 0.125),
                           ((strategy, strategy, (100, 0, 0, 0, 0)), 0.375),
                           ((strategy, (100, 0, 0, 0, 0), (100, 0, 0, 0, 0)), 0.375),
                           (((100, 0, 0, 0, 0),) * 3, 0.125)])
        self.assertAlmostEqual(expected_payout(strategy, population), expected)
        self.assertAlmostEqual(expected_payout(strategy, {strategy: 1.0}), 3.75)

    def test_rank_tie_averages_payout_positions(self):
        players = ((100, 0, 0, 0, 0), (0, 100, 0, 0, 0),
                   (0, 0, 100, 0, 0), (0, 0, 0, 100, 0))
        result = payout(players)
        self.assertAlmostEqual(sum(result), 15.0)


if __name__ == "__main__":
    unittest.main()
