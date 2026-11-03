"""Full-action fictitious play using the exact Game 1 response oracle."""

from collections import Counter
from dataclasses import dataclass
import random

from ...common.allocation import Allocation, SOLDIERS
from .best_response import best_response_from_counts, best_response_from_marginals


@dataclass(frozen=True)
class Result:
    rounds: int
    row_strategy: dict[Allocation, float]
    column_strategy: dict[Allocation, float]
    row_deviation_score: float
    column_deviation_score: float
    row_response: Allocation
    column_response: Allocation
    row_deviation_fraction: tuple[int, int]
    column_deviation_fraction: tuple[int, int]


def solve(rounds: int = 1_000, seed: int = 1, soldiers: int = SOLDIERS) -> Result:
    """Run two-sided fictitious play in the full allocation game.

    Every iterate is a best response in the full action space. The average
    strategies are approximate; exploitability is measured by a fresh exact DP
    best response at termination. This is not an exact equilibrium certificate.
    """
    if rounds < 1:
        raise ValueError("rounds must be positive")
    rng = random.Random(seed)
    initial = [(soldiers // 5,) * 4 + (soldiers - 4 * (soldiers // 5),)]
    # Seed the empirical counts with strategically distinct legal actions.
    initial.extend(tuple(soldiers if i == j else 0 for i in range(5)) for j in range(5))
    initial.extend(_random_allocation(soldiers, rng) for _ in range(20))
    row_counts: Counter[Allocation] = Counter(initial)
    col_counts: Counter[Allocation] = Counter(initial)
    row_marginals = _marginals(row_counts, soldiers)
    col_marginals = _marginals(col_counts, soldiers)
    row_total = col_total = len(initial)

    for _ in range(rounds):
        row_action, _ = best_response_from_marginals(col_marginals, col_total, soldiers)
        col_action, _ = best_response_from_marginals(row_marginals, row_total, soldiers)
        row_counts[row_action] += 1
        col_counts[col_action] += 1
        _add_to_marginals(row_marginals, row_action, 1.0)
        _add_to_marginals(col_marginals, col_action, 1.0)
        row_total += 1
        col_total += 1

    row_total = sum(row_counts.values())
    col_total = sum(col_counts.values())
    row_mix = {a: n / row_total for a, n in row_counts.items()}
    col_mix = {a: n / col_total for a, n in col_counts.items()}
    row_response, row_num, row_den = best_response_from_counts(
        tuple([int(x) for x in row] for row in col_marginals), soldiers)
    col_response, col_num, col_den = best_response_from_counts(
        tuple([int(x) for x in row] for row in row_marginals), soldiers)
    row_score, col_score = row_num / row_den, col_num / col_den
    return Result(rounds, row_mix, col_mix, row_score, col_score,
                  row_response, col_response, (row_num, row_den), (col_num, col_den))


def _marginals(counts: Counter[Allocation], soldiers: int) -> list[list[float]]:
    result = [[0.0] * (soldiers + 1) for _ in range(5)]
    for allocation, count in counts.items():
        for castle, number in enumerate(allocation):
            result[castle][number] += count
    return result


def _add_to_marginals(marginals: list[list[float]], allocation: Allocation,
                      weight: float) -> None:
    for castle, number in enumerate(allocation):
        marginals[castle][number] += weight


def _random_allocation(soldiers: int, rng: random.Random) -> Allocation:
    bars = sorted(rng.sample(range(soldiers + 4), 4))
    cuts = [-1, *bars, soldiers + 4]
    return tuple(cuts[i + 1] - cuts[i] - 1 for i in range(5))  # type: ignore[return-value]
