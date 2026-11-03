"""Exact expected-payoff tools against finite Game 2 populations."""

from collections.abc import Iterable, Mapping
import itertools
import math

from ...common.allocation import Allocation, validate
from .rules import payout


def expected_payout(strategy: Allocation, population: Mapping[Allocation, float]) -> float:
    """Exact expected payout against three iid draws from a finite mixture.

    Opponent triples are aggregated as multisets with their multinomial
    probabilities. Cost is O(K^3) profile scores for support size K; this is
    exact for that finite mixture and makes no claim about omitted strategies.
    """
    validate(strategy)
    if not population:
        raise ValueError("population must not be empty")
    actions = list(population)
    weights = [population[a] for a in actions]
    if any(not math.isfinite(w) or w < 0 for w in weights):
        raise ValueError("probability weights must be finite and nonnegative")
    total = sum(weights)
    if total <= 0:
        raise ValueError("population must have positive total mass")
    probabilities = [w / total for w in weights]
    for action in actions:
        validate(action)

    expectation = 0.0
    for i, j, k in itertools.combinations_with_replacement(range(len(actions)), 3):
        indices = (i, j, k)
        multiplicity = 6 // math.prod(math.factorial(indices.count(t)) for t in set(indices))
        probability = multiplicity * probabilities[i] * probabilities[j] * probabilities[k]
        expectation += probability * payout((strategy, actions[i], actions[j], actions[k]))[0]
    return expectation


def best_candidate(strategy_candidates: Iterable[Allocation],
                   population: Mapping[Allocation, float]) -> tuple[Allocation, float]:
    """Return best action in a supplied candidate set (not a full-game oracle)."""
    candidates = iter(strategy_candidates)
    try:
        best = next(candidates)
    except StopIteration as exc:
        raise ValueError("candidate set must not be empty") from exc
    best_value = expected_payout(best, population)
    for candidate in candidates:
        value = expected_payout(candidate, population)
        if value > best_value:
            best, best_value = candidate, value
    return best, best_value
