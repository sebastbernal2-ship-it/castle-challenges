"""Scoring rules for the head-to-head game."""

from ...common.allocation import Allocation, SOLDIERS, VALUES, validate


def score(a: Allocation, b: Allocation, soldiers: int = SOLDIERS) -> float:
    """Castle points earned by a against b; tied castles are split."""
    validate(a, soldiers)
    validate(b, soldiers)
    return sum(v if x > y else 0.0 if x < y else v / 2
               for x, y, v in zip(a, b, VALUES))
