import unittest

from castle_challenges.games.four_way.rules import castle_points, payout


class FourWayTests(unittest.TestCase):
    def test_all_players_tied(self):
        strategy = (50, 50, 0, 0, 0)
        players = (strategy,) * 4
        self.assertEqual(castle_points(players), (3.75,) * 4)
        self.assertEqual(payout(players), (3.75,) * 4)

    def test_payouts_sum_to_pool(self):
        players = ((100, 0, 0, 0, 0), (0, 100, 0, 0, 0),
                   (0, 0, 100, 0, 0), (0, 0, 0, 100, 0))
        self.assertAlmostEqual(sum(payout(players)), 15.0)

    def test_rank_tie_averages_payout_positions(self):
        players = ((100, 0, 0, 0, 0), (0, 100, 0, 0, 0),
                   (0, 0, 100, 0, 0), (0, 0, 0, 100, 0))
        result = payout(players)
        self.assertAlmostEqual(sum(result), 15.0)


if __name__ == "__main__":
    unittest.main()
