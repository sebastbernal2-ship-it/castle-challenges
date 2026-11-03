"""Full-action fictitious play using the exact Game 1 response oracle."""

from collections import Counter
from dataclasses import dataclass
import random

from ...common.allocation import Allocation, SOLDIERS
from .best_response import best_response


@dataclass(frozen=True)
class Result:
    rounds: int
    row_strategy: dict[Allocation, float]
    column_strategy: dict[Allocation, float]
    row_deviation_score: float
    column_deviation_score: float
    row_response: Allocation
    column_response: Allocation


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

    for _ in range(rounds):
        row_action, _ = best_response(col_counts, soldiers)
        col_action, _ = best_response(row_counts, soldiers)
        row_counts[row_action] += 1
        col_counts[col_action] += 1

    row_total = sum(row_counts.values())
    col_total = sum(col_counts.values())
    row_mix = {a: n / row_total for a, n in row_counts.items()}
    col_mix = {a: n / col_total for a, n in col_counts.items()}
    row_response, row_score = best_response(col_mix, soldiers)
    col_response, col_score = best_response(row_mix, soldiers)
    return Result(rounds, row_mix, col_mix, row_score, col_score,
                  row_response, col_response)


def _random_allocation(soldiers: int, rng: random.Random) -> Allocation:
    bars = sorted(rng.sample(range(soldiers + 4), 4))
    cuts = [-1, *bars, soldiers + 4]
    return tuple(cuts[i + 1] - cuts[i] - 1 for i in range(5))  # type: ignore[return-value]
