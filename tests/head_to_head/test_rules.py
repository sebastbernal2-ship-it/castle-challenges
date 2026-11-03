import unittest

from castle_challenges.common.allocation import allocations
from castle_challenges.games.head_to_head.best_response import best_response
from castle_challenges.games.head_to_head.evaluation import evaluate
from castle_challenges.games.head_to_head.fictitious_play import solve
from castle_challenges.games.head_to_head.rules import score


class HeadToHeadTests(unittest.TestCase):
    def test_allocation_count_and_sum(self):
        self.assertEqual(sum(1 for _ in allocations(4)), 70)
        self.assertTrue(all(sum(a) == 4 for a in allocations(4)))

    def test_scoring(self):
        even = (20, 20, 20, 20, 20)
        self.assertEqual(score(even, even), 7.5)
        self.assertEqual(score((100, 0, 0, 0, 0), (0, 0, 0, 0, 100)), 5.5)
        self.assertAlmostEqual(score(even, (0, 0, 0, 0, 100)) +
                               score((0, 0, 0, 0, 100), even), 15.0)

    def test_exact_best_response_matches_brute_force_small_game(self):
        opponent = {(3, 0, 0, 0, 0): 2, (0, 1, 1, 1, 0): 1}
        response, value = best_response(opponent, soldiers=3)
        brute = max(sum(weight * score(candidate, other, soldiers=3) for other, weight in opponent.items()) / 3
                    for candidate in allocations(3))
        self.assertAlmostEqual(value, brute)
        self.assertAlmostEqual(sum(response), 3)

    def test_fictitious_play_returns_legal_strategies(self):
        result = solve(rounds=2, seed=2, soldiers=3)
        self.assertAlmostEqual(sum(result.row_strategy.values()), 1.0)
        self.assertAlmostEqual(sum(result.column_strategy.values()), 1.0)
        self.assertEqual(sum(result.row_response), 3)

    def test_rejects_non_100_soldier_profiles(self):
        with self.assertRaises(ValueError):
            score((0, 0, 0, 0, 0), (0, 0, 0, 0, 0))

    def test_simulation_seed_reproducible(self):
        even = (20, 20, 20, 20, 20)
        self.assertEqual(evaluate(even, [even], 50, 3), evaluate(even, [even], 50, 3))


if __name__ == "__main__":
    unittest.main()
