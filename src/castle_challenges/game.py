"""Exact game rules for the two castle allocation challenges."""

from typing import TypeAlias

Allocation: TypeAlias = tuple[int, int, int, int, int]
VALUES = (1, 2, 3, 4, 5)
PAYOUTS = (9.0, 4.0, 2.0, 0.0)
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


def head_to_head(a: Allocation, b: Allocation) -> float:
    """Castle points won by a; tied castles are split."""
    validate(a, sum(a))
    validate(b, sum(b))
    return sum(v if x > y else 0.0 if x < y else v / 2
               for x, y, v in zip(a, b, VALUES))


def castle_points(players: tuple[Allocation, ...]) -> tuple[float, ...]:
    """Return points per player after independently splitting each castle."""
    if not players:
        raise ValueError("at least one player is required")
    for p in players:
        validate(p, sum(p))
    totals = [0.0] * len(players)
    for castle, value in enumerate(VALUES):
        high = max(p[castle] for p in players)
        winners = [i for i, p in enumerate(players) if p[castle] == high]
        for i in winners:
            totals[i] += value / len(winners)
    return tuple(totals)


def four_way_payout(players: tuple[Allocation, Allocation, Allocation, Allocation]) -> tuple[float, ...]:
    """Tournament payout per player, averaging payout across tied rank slots."""
    if len(players) != 4:
        raise ValueError("four-way game requires exactly four players")
    scores = castle_points(players)
    order = sorted(range(4), key=lambda i: scores[i], reverse=True)
    result = [0.0] * 4
    start = 0
    while start < 4:
        end = start + 1
        while end < 4 and scores[order[end]] == scores[order[start]]:
            end += 1
        payout = sum(PAYOUTS[start:end]) / (end - start)
        for position in range(start, end):
            result[order[position]] = payout
        start = end
    return tuple(result)
