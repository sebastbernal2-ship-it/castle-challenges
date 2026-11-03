"""Monte Carlo evaluation for Game 1 only."""

import random
from collections.abc import Sequence

from ...common.allocation import Allocation, validate
from .rules import score


def evaluate(strategy: Allocation, population: Sequence[Allocation], trials: int = 10_000,
             seed: int | None = None) -> tuple[float, float]:
    """Return (mean castle score, standard error) versus sampled population members."""
    validate(strategy)
    if not population or trials <= 0:
        raise ValueError("population and positive trial count are required")
    rng = random.Random(seed)
    samples = [score(strategy, rng.choice(population)) for _ in range(trials)]
    mean = sum(samples) / len(samples)
    if len(samples) < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in samples) / (len(samples) - 1)
    return mean, (variance / len(samples)) ** 0.5
