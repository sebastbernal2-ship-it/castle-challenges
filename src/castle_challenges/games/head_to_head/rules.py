"""Scoring rules for the head-to-head game."""

from ...common.allocation import Allocation, VALUES, validate


def score(a: Allocation, b: Allocation) -> float:
    """Castle points earned by a against b; tied castles are split."""
    validate(a, sum(a))
    validate(b, sum(b))
    return sum(v if x > y else 0.0 if x < y else v / 2
               for x, y, v in zip(a, b, VALUES))
