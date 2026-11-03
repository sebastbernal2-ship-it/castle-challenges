import unittest

from castle_challenges.common.allocation import allocations
from castle_challenges.games.head_to_head.best_response import best_response
from castle_challenges.games.head_to_head.evaluation import evaluate
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
        brute = max(sum(weight * score(candidate, other) for other, weight in opponent.items()) / 3
                    for candidate in allocations(3))
        self.assertAlmostEqual(value, brute)
        self.assertAlmostEqual(sum(response), 3)

    def test_simulation_seed_reproducible(self):
        even = (20, 20, 20, 20, 20)
        self.assertEqual(evaluate(even, [even], 50, 3), evaluate(even, [even], 50, 3))


if __name__ == "__main__":
    unittest.main()
