"""Exact dynamic-programming best response for Game 1 mixtures."""

from collections.abc import Mapping
import math

from ...common.allocation import Allocation, SOLDIERS, VALUES, validate


def payoff_tables(opponent: Mapping[Allocation, float], soldiers: int = SOLDIERS
                  ) -> tuple[tuple[float, ...], ...]:
    """Return q[castle][x] expected castle score for assigning x soldiers.

    `opponent` maps legal allocations to nonnegative probability mass. Weights
    are normalized internally, so any positive finite total mass is accepted.
    """
    if not opponent:
        raise ValueError("opponent distribution must not be empty")
    total = 0.0
    marginals = [[0.0] * (soldiers + 1) for _ in VALUES]
    for allocation, weight in opponent.items():
        validate(allocation, soldiers)
        if not math.isfinite(weight) or weight < 0:
            raise ValueError("probability weights must be finite and nonnegative")
        total += weight
        for i, soldiers_at_castle in enumerate(allocation):
            marginals[i][soldiers_at_castle] += weight
    if total <= 0:
        raise ValueError("opponent distribution must have positive total mass")

    tables = []
    for i, value in enumerate(VALUES):
        cumulative = 0.0
        row = []
        for x, mass in enumerate(marginals[i]):
            row.append(value * (cumulative + mass / 2) / total)
            cumulative += mass
        tables.append(tuple(row))
    return tuple(tables)


def best_response(opponent: Mapping[Allocation, float], soldiers: int = SOLDIERS
                 ) -> tuple[Allocation, float]:
    """Return a pure allocation maximizing expected score against a mixture.

    The dynamic program is exact up to floating-point arithmetic. The returned
    value is the expected score (whose game value is 7.5 in equilibrium).
    """
    tables = payoff_tables(opponent, soldiers)
    # dp[i][t] is the best contribution from castles [0, i) using t soldiers.
    dp = [[-math.inf] * (soldiers + 1) for _ in range(len(VALUES) + 1)]
    choice = [[0] * (soldiers + 1) for _ in range(len(VALUES) + 1)]
    dp[0][0] = 0.0
    for i in range(1, len(VALUES) + 1):
        row = tables[i - 1]
        for used in range(soldiers + 1):
            for x in range(used + 1):
                candidate = dp[i - 1][used - x] + row[x]
                if candidate > dp[i][used]:
                    dp[i][used] = candidate
                    choice[i][used] = x
    allocation = [0] * len(VALUES)
    remaining = soldiers
    for i in range(len(VALUES), 0, -1):
        allocation[i - 1] = choice[i][remaining]
        remaining -= allocation[i - 1]
    return tuple(allocation), dp[len(VALUES)][soldiers]  # type: ignore[return-value]
