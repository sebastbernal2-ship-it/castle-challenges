"""Monte Carlo evaluation for Game 2 only."""

import random
from collections.abc import Sequence

from ...common.allocation import Allocation, validate
from .rules import payout


def evaluate(strategy: Allocation, population: Sequence[Allocation], trials: int = 10_000,
             seed: int | None = None) -> tuple[float, float]:
    """Return (mean tournament payout, standard error).

    Three opponents are independently sampled with replacement from the population.
    """
    validate(strategy)
    if not population or trials <= 0:
        raise ValueError("population and positive trial count are required")
    rng = random.Random(seed)
    samples = [payout((strategy, *(rng.choice(population) for _ in range(3))))[0]
               for _ in range(trials)]
    mean = sum(samples) / len(samples)
    if len(samples) < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in samples) / (len(samples) - 1)
    return mean, (variance / len(samples)) ** 0.5
