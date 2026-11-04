import unittest

from castle_challenges.games.four_way.rules import payout
from research.four_way.response_equivalence import (
    build_response_classes,
    exact_top_responses,
)


class ResponseEquivalenceTests(unittest.TestCase):
    def test_exact_three_action_quotient_and_ranking(self):
        support = [
            (20, 20, 20, 20, 20),
            (19, 20, 20, 20, 21),
            (0, 0, 0, 0, 100),
        ]
        classes = build_response_classes(support)
        self.assertEqual(len(classes.representatives), 93)
        self.assertEqual(sum(classes.class_sizes), 4_598_123)
        self.assertTrue(all(a not in support for a in classes.representatives))
        self.assertEqual(classes.payouts_quarters.shape, (93, 10))

        for representative, row in zip(classes.representatives,
                                        classes.payouts_quarters):
            expected = []
            for i, j, k in classes.triples:
                result = payout((representative, support[i], support[j], support[k]))[0]
                expected.append(round(4 * result))
            self.assertEqual(list(row), expected)

        frequencies = [300, 700, 0]
        action, numerator, denominator, _size = exact_top_responses(
            classes, frequencies, top_k=1
        )[0]
        direct_numerator = 0
        class_index = classes.representatives.index(action)
        signature = classes.payouts_quarters[class_index]
        for scenario, (i, j, k) in enumerate(classes.triples):
            multiplicity = 1 if i == k else 3 if i == j or j == k else 6
            direct_numerator += int(signature[scenario]) * (
                multiplicity * frequencies[i] * frequencies[j] * frequencies[k]
            )
        self.assertEqual(numerator, direct_numerator)
        self.assertEqual(denominator, 4 * sum(frequencies) ** 3)


if __name__ == "__main__":
    unittest.main()
