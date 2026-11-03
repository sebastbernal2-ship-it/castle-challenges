"""Seeded Monte Carlo evaluation against an empirical strategy population."""

import random
from collections.abc import Sequence

from .game import Allocation, four_way_payout, head_to_head, validate


def evaluate_head_to_head(strategy: Allocation, population: Sequence[Allocation],
                          trials: int = 10_000, seed: int | None = None) -> tuple[float, float]:
    """Return (mean score, standard error) versus uniformly sampled population members."""
    validate(strategy)
    if not population or trials <= 0:
        raise ValueError("population and positive trial count are required")
    rng = random.Random(seed)
    samples = [head_to_head(strategy, rng.choice(population)) for _ in range(trials)]
    return _mean_se(samples)


def evaluate_four_way(strategy: Allocation, population: Sequence[Allocation],
                      trials: int = 10_000, seed: int | None = None) -> tuple[float, float]:
    """Return (mean payout, standard error) in groups of four.

    The three opponents are sampled independently with replacement. This models
    independent draws from an empirical population, not sampling without replacement.
    """
    validate(strategy)
    if not population or trials <= 0:
        raise ValueError("population and positive trial count are required")
    rng = random.Random(seed)
    samples = [four_way_payout((strategy, *(rng.choice(population) for _ in range(3))))[0]
               for _ in range(trials)]
    return _mean_se(samples)


def _mean_se(samples: list[float]) -> tuple[float, float]:
    mean = sum(samples) / len(samples)
    if len(samples) < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in samples) / (len(samples) - 1)
    return mean, (variance / len(samples)) ** 0.5
