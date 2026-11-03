"""Shared representation and legal-allocation helpers."""

from typing import TypeAlias

Allocation: TypeAlias = tuple[int, int, int, int, int]
VALUES = (1, 2, 3, 4, 5)
SOLDIERS = 100


def validate(allocation: Allocation, soldiers: int = SOLDIERS) -> None:
    if len(allocation) != 5 or any(type(x) is not int or x < 0 for x in allocation):
        raise ValueError("allocation must contain five nonnegative integers")
    if sum(allocation) != soldiers:
        raise ValueError(f"allocation must sum to {soldiers}")


def allocations(soldiers: int = SOLDIERS):
    """Yield every legal allocation exactly once (stars and bars order)."""
    if soldiers < 0:
        raise ValueError("soldiers must be nonnegative")
    for a in range(soldiers + 1):
        for b in range(soldiers - a + 1):
            for c in range(soldiers - a - b + 1):
                for d in range(soldiers - a - b - c + 1):
                    yield (a, b, c, d, soldiers - a - b - c - d)
